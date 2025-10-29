"""
Mock implementations for message queue systems.

Provides mock implementations for:
- RabbitMQ message broker operations (pika)
- Redis pub/sub messaging
- Celery distributed task queue
- Generic in-memory message queue with FIFO operations

All implementations are thread-safe and suitable for testing asynchronous
workflows without requiring actual message broker connections.
"""

import json
import time
import uuid
from collections import defaultdict, deque, Counter
from copy import deepcopy
from datetime import datetime, timedelta
from queue import Queue, Empty, Full
from threading import Lock, RLock, Thread, Event
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from unittest.mock import MagicMock

import pytest


class MockRabbitMQChannel:
    """
    Mock implementation of a RabbitMQ channel (pika.channel.Channel).
    
    Provides in-memory message publishing, consuming, queue and exchange
    management without requiring actual RabbitMQ connection. Thread-safe
    for concurrent testing scenarios.
    """
    
    def __init__(self):
        """Initialize mock RabbitMQ channel with empty state."""
        self._lock = RLock()
        self._queues: Dict[str, MockMessageQueue] = {}
        self._exchanges: Dict[str, Dict[str, Any]] = {}
        self._bindings: Dict[str, List[str]] = defaultdict(list)  # exchange -> queues
        self._published_messages: List[Dict[str, Any]] = []
        self._consumed_messages: List[Dict[str, Any]] = []
        self._delivery_tag_counter = 0
        self._consumers: Dict[str, Callable] = {}
        self.is_open = True
        
    def basic_publish(
        self,
        exchange: str,
        routing_key: str,
        body: Union[str, bytes],
        properties: Optional[Any] = None,
        mandatory: bool = False
    ) -> bool:
        """
        Publish a message to an exchange with routing key.
        
        Args:
            exchange: Exchange name to publish to
            routing_key: Routing key for message routing
            body: Message body (string or bytes)
            properties: Message properties (headers, delivery_mode, etc.)
            mandatory: If True, raise exception if message cannot be routed
            
        Returns:
            True if message published successfully
            
        Raises:
            Exception: If channel is closed or mandatory routing fails
        """
        with self._lock:
            if not self.is_open:
                raise Exception("Channel is closed")
            
            # Convert bytes to string for storage
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            
            message = {
                'exchange': exchange,
                'routing_key': routing_key,
                'body': body,
                'properties': properties,
                'timestamp': datetime.now().isoformat(),
                'message_id': str(uuid.uuid4())
            }
            
            self._published_messages.append(deepcopy(message))
            
            # Route message to bound queues
            routed = False
            if exchange in self._bindings:
                for queue_name in self._bindings[exchange]:
                    if queue_name in self._queues:
                        self._queues[queue_name].enqueue(deepcopy(message))
                        routed = True
            
            # For default exchange, route directly to queue with name=routing_key
            if exchange == '' and routing_key in self._queues:
                self._queues[routing_key].enqueue(deepcopy(message))
                routed = True
            
            if mandatory and not routed:
                raise Exception(f"Message could not be routed: {routing_key}")
            
            return True
    
    def basic_consume(
        self,
        queue: str,
        on_message_callback: Callable,
        auto_ack: bool = False,
        exclusive: bool = False,
        consumer_tag: Optional[str] = None
    ) -> str:
        """
        Start consuming messages from a queue.
        
        Args:
            queue: Queue name to consume from
            on_message_callback: Callback function for message handling
            auto_ack: Automatically acknowledge messages
            exclusive: Exclusive consumer access
            consumer_tag: Consumer identifier
            
        Returns:
            Consumer tag string
        """
        with self._lock:
            if not self.is_open:
                raise Exception("Channel is closed")
            
            if queue not in self._queues:
                raise Exception(f"Queue '{queue}' not found")
            
            if consumer_tag is None:
                consumer_tag = f"ctag-{uuid.uuid4()}"
            
            self._consumers[consumer_tag] = {
                'queue': queue,
                'callback': on_message_callback,
                'auto_ack': auto_ack,
                'exclusive': exclusive
            }
            
            return consumer_tag
    
    def queue_declare(
        self,
        queue: str,
        passive: bool = False,
        durable: bool = False,
        exclusive: bool = False,
        auto_delete: bool = False,
        arguments: Optional[Dict] = None
    ) -> MagicMock:
        """
        Declare a queue.
        
        Args:
            queue: Queue name
            passive: Only check if queue exists
            durable: Queue survives broker restart
            exclusive: Queue is exclusive to connection
            auto_delete: Queue deleted when last consumer unsubscribes
            arguments: Additional queue arguments
            
        Returns:
            Mock method object with queue metadata
        """
        with self._lock:
            if passive:
                if queue not in self._queues:
                    raise Exception(f"Queue '{queue}' does not exist")
            else:
                if queue not in self._queues:
                    self._queues[queue] = MockMessageQueue(maxsize=0)
            
            # Return mock method object
            result = MagicMock()
            result.method.queue = queue
            result.method.message_count = self._queues[queue].size() if queue in self._queues else 0
            result.method.consumer_count = sum(
                1 for c in self._consumers.values() if c['queue'] == queue
            )
            return result
    
    def exchange_declare(
        self,
        exchange: str,
        exchange_type: str = 'direct',
        passive: bool = False,
        durable: bool = False,
        auto_delete: bool = False,
        internal: bool = False,
        arguments: Optional[Dict] = None
    ) -> MagicMock:
        """
        Declare an exchange.
        
        Args:
            exchange: Exchange name
            exchange_type: Type (direct, fanout, topic, headers)
            passive: Only check if exchange exists
            durable: Exchange survives broker restart
            auto_delete: Exchange deleted when last queue unbinds
            internal: Exchange cannot be published to directly
            arguments: Additional exchange arguments
            
        Returns:
            Mock method object
        """
        with self._lock:
            if passive:
                if exchange not in self._exchanges:
                    raise Exception(f"Exchange '{exchange}' does not exist")
            else:
                if exchange not in self._exchanges:
                    self._exchanges[exchange] = {
                        'type': exchange_type,
                        'durable': durable,
                        'auto_delete': auto_delete,
                        'internal': internal,
                        'arguments': arguments or {}
                    }
            
            result = MagicMock()
            return result
    
    def basic_ack(self, delivery_tag: int, multiple: bool = False) -> None:
        """
        Acknowledge message delivery.
        
        Args:
            delivery_tag: Message delivery tag
            multiple: Acknowledge all messages up to delivery_tag
        """
        # Track acknowledgment for testing verification
        pass
    
    def basic_nack(
        self,
        delivery_tag: int,
        multiple: bool = False,
        requeue: bool = True
    ) -> None:
        """
        Negative acknowledge (reject) message delivery.
        
        Args:
            delivery_tag: Message delivery tag
            multiple: Reject all messages up to delivery_tag
            requeue: Requeue the message
        """
        pass
    
    def basic_reject(self, delivery_tag: int, requeue: bool = True) -> None:
        """
        Reject a single message.
        
        Args:
            delivery_tag: Message delivery tag
            requeue: Requeue the message
        """
        pass
    
    def queue_bind(
        self,
        queue: str,
        exchange: str,
        routing_key: Optional[str] = None,
        arguments: Optional[Dict] = None
    ) -> MagicMock:
        """
        Bind queue to exchange with routing key.
        
        Args:
            queue: Queue name
            exchange: Exchange name
            routing_key: Routing key pattern
            arguments: Binding arguments
            
        Returns:
            Mock method object
        """
        with self._lock:
            if queue not in self._queues:
                raise Exception(f"Queue '{queue}' not found")
            if exchange not in self._exchanges and exchange != '':
                raise Exception(f"Exchange '{exchange}' not found")
            
            if queue not in self._bindings[exchange]:
                self._bindings[exchange].append(queue)
            
            return MagicMock()
    
    def queue_purge(self, queue: str) -> MagicMock:
        """
        Purge all messages from queue.
        
        Args:
            queue: Queue name
            
        Returns:
            Mock method object with message count
        """
        with self._lock:
            if queue not in self._queues:
                raise Exception(f"Queue '{queue}' not found")
            
            message_count = self._queues[queue].size()
            self._queues[queue].clear()
            
            result = MagicMock()
            result.method.message_count = message_count
            return result
    
    def queue_delete(
        self,
        queue: str,
        if_unused: bool = False,
        if_empty: bool = False
    ) -> MagicMock:
        """
        Delete a queue.
        
        Args:
            queue: Queue name
            if_unused: Only delete if no consumers
            if_empty: Only delete if no messages
            
        Returns:
            Mock method object with message count
        """
        with self._lock:
            if queue not in self._queues:
                raise Exception(f"Queue '{queue}' not found")
            
            message_count = self._queues[queue].size()
            
            if if_unused:
                consumer_count = sum(1 for c in self._consumers.values() if c['queue'] == queue)
                if consumer_count > 0:
                    raise Exception(f"Queue '{queue}' has active consumers")
            
            if if_empty and message_count > 0:
                raise Exception(f"Queue '{queue}' is not empty")
            
            del self._queues[queue]
            
            result = MagicMock()
            result.method.message_count = message_count
            return result
    
    def exchange_delete(
        self,
        exchange: str,
        if_unused: bool = False
    ) -> MagicMock:
        """
        Delete an exchange.
        
        Args:
            exchange: Exchange name
            if_unused: Only delete if no bindings
            
        Returns:
            Mock method object
        """
        with self._lock:
            if exchange not in self._exchanges:
                raise Exception(f"Exchange '{exchange}' not found")
            
            if if_unused and exchange in self._bindings and self._bindings[exchange]:
                raise Exception(f"Exchange '{exchange}' has bindings")
            
            del self._exchanges[exchange]
            if exchange in self._bindings:
                del self._bindings[exchange]
            
            return MagicMock()
    
    def get_published_messages(self) -> List[Dict[str, Any]]:
        """
        Get all published messages for test verification.
        
        Returns:
            List of published message dictionaries
        """
        with self._lock:
            return deepcopy(self._published_messages)
    
    def get_consumed_messages(self) -> List[Dict[str, Any]]:
        """
        Get all consumed messages for test verification.
        
        Returns:
            List of consumed message dictionaries
        """
        with self._lock:
            return deepcopy(self._consumed_messages)
    
    def clear_history(self) -> None:
        """Clear all message history for fresh test state."""
        with self._lock:
            self._published_messages.clear()
            self._consumed_messages.clear()


class MockRedisPublisher:
    """
    Mock implementation of Redis pub/sub messaging.
    
    Provides in-memory publish/subscribe operations without requiring
    actual Redis connection. Thread-safe for concurrent testing.
    """
    
    def __init__(self):
        """Initialize mock Redis publisher with empty state."""
        self._lock = RLock()
        self._channels: Dict[str, MockMessageQueue] = {}
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._pattern_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._published_messages: List[Dict[str, Any]] = []
    
    def publish(self, channel: str, message: Union[str, bytes, dict]) -> int:
        """
        Publish message to channel.
        
        Args:
            channel: Channel name
            message: Message to publish (string, bytes, or dict)
            
        Returns:
            Number of subscribers that received the message
        """
        with self._lock:
            # Serialize message if dict
            if isinstance(message, dict):
                message = json.dumps(message)
            elif isinstance(message, bytes):
                message = message.decode('utf-8')
            
            msg_data = {
                'channel': channel,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'message_id': str(uuid.uuid4())
            }
            
            self._published_messages.append(deepcopy(msg_data))
            
            # Deliver to channel subscribers
            subscriber_count = 0
            if channel in self._subscribers:
                for callback in self._subscribers[channel]:
                    callback(deepcopy(msg_data))
                    subscriber_count += 1
            
            # Deliver to pattern subscribers
            for pattern, callbacks in self._pattern_subscribers.items():
                if self._match_pattern(channel, pattern):
                    for callback in callbacks:
                        callback(deepcopy(msg_data))
                        subscriber_count += 1
            
            return subscriber_count
    
    def subscribe(self, channel: str, callback: Optional[Callable] = None) -> None:
        """
        Subscribe to a channel.
        
        Args:
            channel: Channel name
            callback: Optional callback function for messages
        """
        with self._lock:
            if channel not in self._channels:
                self._channels[channel] = MockMessageQueue(maxsize=0)
            
            if callback is not None:
                if callback not in self._subscribers[channel]:
                    self._subscribers[channel].append(callback)
    
    def psubscribe(self, pattern: str, callback: Optional[Callable] = None) -> None:
        """
        Subscribe to channels matching a pattern.
        
        Args:
            pattern: Channel pattern (e.g., 'user.*')
            callback: Optional callback function for messages
        """
        with self._lock:
            if callback is not None:
                if callback not in self._pattern_subscribers[pattern]:
                    self._pattern_subscribers[pattern].append(callback)
    
    def unsubscribe(self, channel: str, callback: Optional[Callable] = None) -> None:
        """
        Unsubscribe from a channel.
        
        Args:
            channel: Channel name
            callback: Optional specific callback to remove
        """
        with self._lock:
            if callback is None:
                # Remove all subscribers
                if channel in self._subscribers:
                    self._subscribers[channel].clear()
            else:
                # Remove specific callback
                if channel in self._subscribers and callback in self._subscribers[channel]:
                    self._subscribers[channel].remove(callback)
    
    def punsubscribe(self, pattern: str, callback: Optional[Callable] = None) -> None:
        """
        Unsubscribe from pattern.
        
        Args:
            pattern: Channel pattern
            callback: Optional specific callback to remove
        """
        with self._lock:
            if callback is None:
                # Remove all pattern subscribers
                if pattern in self._pattern_subscribers:
                    self._pattern_subscribers[pattern].clear()
            else:
                # Remove specific callback
                if pattern in self._pattern_subscribers and callback in self._pattern_subscribers[pattern]:
                    self._pattern_subscribers[pattern].remove(callback)
    
    def get_published_messages(self, channel: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get published messages for test verification.
        
        Args:
            channel: Optional channel filter
            
        Returns:
            List of published message dictionaries
        """
        with self._lock:
            if channel is None:
                return deepcopy(self._published_messages)
            else:
                return deepcopy([
                    msg for msg in self._published_messages
                    if msg['channel'] == channel
                ])
    
    def get_subscribers(self, channel: str) -> int:
        """
        Get number of subscribers for channel.
        
        Args:
            channel: Channel name
            
        Returns:
            Number of subscribers
        """
        with self._lock:
            count = len(self._subscribers.get(channel, []))
            # Add pattern subscribers
            for pattern in self._pattern_subscribers:
                if self._match_pattern(channel, pattern):
                    count += len(self._pattern_subscribers[pattern])
            return count
    
    def clear_history(self) -> None:
        """Clear all message history for fresh test state."""
        with self._lock:
            self._published_messages.clear()
    
    @staticmethod
    def _match_pattern(channel: str, pattern: str) -> bool:
        """
        Simple pattern matching for Redis patterns.
        
        Args:
            channel: Channel name
            pattern: Pattern with * wildcard
            
        Returns:
            True if channel matches pattern
        """
        # Simple implementation: convert * to regex
        import re
        regex_pattern = pattern.replace('*', '.*')
        return bool(re.match(f'^{regex_pattern}$', channel))


class MockCeleryTask:
    """
    Mock implementation of Celery distributed task.
    
    Simulates asynchronous task execution without actual Celery worker.
    Provides task state tracking, result retrieval, and execution history.
    """
    
    # Task state constants
    PENDING = 'PENDING'
    STARTED = 'STARTED'
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'
    RETRY = 'RETRY'
    REVOKED = 'REVOKED'
    
    def __init__(self, task_func: Optional[Callable] = None, task_id: Optional[str] = None):
        """
        Initialize mock Celery task.
        
        Args:
            task_func: Actual function to execute
            task_id: Task identifier
        """
        self._lock = RLock()
        self._task_func = task_func
        self.task_id = task_id or str(uuid.uuid4())
        self._state = self.PENDING
        self._result = None
        self._exception = None
        self._task_history: List[Dict[str, Any]] = []
        self._retry_count = 0
        self._max_retries = 3
        self._executed = False
    
    def apply_async(
        self,
        args: Optional[Tuple] = None,
        kwargs: Optional[Dict] = None,
        countdown: Optional[int] = None,
        eta: Optional[datetime] = None,
        retry: bool = False,
        retry_policy: Optional[Dict] = None,
        **options
    ) -> 'MockCeleryTask':
        """
        Execute task asynchronously.
        
        Args:
            args: Positional arguments for task
            kwargs: Keyword arguments for task
            countdown: Delay in seconds before execution
            eta: Specific time to execute
            retry: Enable retry on failure
            retry_policy: Retry policy configuration
            **options: Additional task options
            
        Returns:
            Self for chaining and result retrieval
        """
        with self._lock:
            args = args or ()
            kwargs = kwargs or {}
            
            task_record = {
                'task_id': self.task_id,
                'args': args,
                'kwargs': kwargs,
                'countdown': countdown,
                'eta': eta.isoformat() if eta else None,
                'submitted_at': datetime.now().isoformat(),
                'state': self.STARTED
            }
            
            self._task_history.append(deepcopy(task_record))
            self._state = self.STARTED
            
            # Simulate execution with optional delay
            if countdown:
                time.sleep(min(countdown, 0.1))  # Cap at 0.1s for testing
            
            # Execute task function if provided
            if self._task_func:
                try:
                    self._result = self._task_func(*args, **kwargs)
                    self._state = self.SUCCESS
                    task_record['state'] = self.SUCCESS
                    task_record['result'] = self._result
                except Exception as exc:
                    self._exception = exc
                    self._state = self.FAILURE
                    task_record['state'] = self.FAILURE
                    task_record['exception'] = str(exc)
                    
                    if retry and self._retry_count < self._max_retries:
                        self._retry_count += 1
                        self._state = self.RETRY
            else:
                # No function provided, simulate success
                self._state = self.SUCCESS
                self._result = {'status': 'completed'}
            
            self._executed = True
            task_record['completed_at'] = datetime.now().isoformat()
            
            return self
    
    def delay(self, *args, **kwargs) -> 'MockCeleryTask':
        """
        Shortcut to apply_async with args/kwargs.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Self for chaining
        """
        return self.apply_async(args=args, kwargs=kwargs)
    
    def get(self, timeout: Optional[float] = None, propagate: bool = True) -> Any:
        """
        Get task result, blocking if necessary.
        
        Args:
            timeout: Maximum time to wait for result
            propagate: Raise exception if task failed
            
        Returns:
            Task result
            
        Raises:
            Exception: If task failed and propagate=True
        """
        with self._lock:
            start_time = time.time()
            
            # Wait for task completion
            while self._state in (self.PENDING, self.STARTED, self.RETRY):
                if timeout and (time.time() - start_time) > timeout:
                    raise TimeoutError(f"Task {self.task_id} timed out")
                time.sleep(0.01)  # Small delay for testing
            
            if self._state == self.FAILURE:
                if propagate and self._exception:
                    raise self._exception
                return None
            
            if self._state == self.REVOKED:
                raise Exception(f"Task {self.task_id} was revoked")
            
            return self._result
    
    def ready(self) -> bool:
        """
        Check if task has completed.
        
        Returns:
            True if task is in final state
        """
        with self._lock:
            return self._state in (self.SUCCESS, self.FAILURE, self.REVOKED)
    
    @property
    def result(self) -> Any:
        """
        Get task result without blocking.
        
        Returns:
            Task result or None if not ready
        """
        with self._lock:
            return self._result
    
    @property
    def state(self) -> str:
        """
        Get current task state.
        
        Returns:
            Task state string
        """
        with self._lock:
            return self._state
    
    @property
    def status(self) -> str:
        """
        Alias for state property.
        
        Returns:
            Task state string
        """
        return self.state
    
    def revoke(self, terminate: bool = False, signal: str = 'SIGTERM') -> None:
        """
        Revoke (cancel) the task.
        
        Args:
            terminate: Terminate task immediately
            signal: Signal to send for termination
        """
        with self._lock:
            if self._state in (self.PENDING, self.STARTED):
                self._state = self.REVOKED
    
    def retry(
        self,
        exc: Optional[Exception] = None,
        countdown: Optional[int] = None,
        max_retries: Optional[int] = None
    ) -> None:
        """
        Retry the task.
        
        Args:
            exc: Exception that caused retry
            countdown: Delay before retry
            max_retries: Maximum retry attempts
        """
        with self._lock:
            if max_retries is not None:
                self._max_retries = max_retries
            
            if self._retry_count < self._max_retries:
                self._retry_count += 1
                self._state = self.RETRY
                if countdown:
                    time.sleep(min(countdown, 0.1))
    
    def get_task_history(self) -> List[Dict[str, Any]]:
        """
        Get complete task execution history.
        
        Returns:
            List of task execution records
        """
        with self._lock:
            return deepcopy(self._task_history)
    
    def clear_history(self) -> None:
        """Clear task execution history."""
        with self._lock:
            self._task_history.clear()
            self._retry_count = 0


class MockMessageQueue:
    """
    Thread-safe in-memory FIFO message queue.
    
    Generic message queue implementation using Python's Queue for
    thread-safe operations. Suitable for testing message-driven
    architectures without external dependencies.
    """
    
    def __init__(self, maxsize: int = 0):
        """
        Initialize message queue.
        
        Args:
            maxsize: Maximum queue size (0 = unlimited)
        """
        self._queue = Queue(maxsize=maxsize)
        self._lock = RLock()
        self._message_counter = 0
    
    def enqueue(self, message: Any, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Add message to queue.
        
        Args:
            message: Message to enqueue
            block: Block if queue is full
            timeout: Maximum time to wait if blocking
            
        Returns:
            True if message was enqueued successfully
            
        Raises:
            Full: If queue is full and block=False
        """
        try:
            with self._lock:
                self._message_counter += 1
                msg_wrapper = {
                    'id': self._message_counter,
                    'data': deepcopy(message),
                    'enqueued_at': datetime.now().isoformat(),
                    'timestamp': time.time()
                }
            
            self._queue.put(msg_wrapper, block=block, timeout=timeout)
            return True
        except Full:
            raise
    
    def dequeue(self, block: bool = True, timeout: Optional[float] = None) -> Optional[Any]:
        """
        Remove and return message from queue.
        
        Args:
            block: Block if queue is empty
            timeout: Maximum time to wait if blocking
            
        Returns:
            Message data or None if queue is empty
            
        Raises:
            Empty: If queue is empty and block=False
        """
        try:
            msg_wrapper = self._queue.get(block=block, timeout=timeout)
            return msg_wrapper['data']
        except Empty:
            if not block:
                return None
            raise
    
    def peek(self) -> Optional[Any]:
        """
        Return next message without removing it.
        
        Returns:
            Next message or None if queue is empty
        """
        with self._lock:
            if self._queue.empty():
                return None
            
            # Get and immediately put back
            try:
                msg_wrapper = self._queue.get_nowait()
                # Put it back at the front (simulate peek)
                # Note: This is not perfect for peek but works for testing
                self._queue.put(msg_wrapper)
                return msg_wrapper['data']
            except Empty:
                return None
    
    def size(self) -> int:
        """
        Get current queue size.
        
        Returns:
            Number of messages in queue
        """
        return self._queue.qsize()
    
    def is_empty(self) -> bool:
        """
        Check if queue is empty.
        
        Returns:
            True if queue has no messages
        """
        return self._queue.empty()
    
    def is_full(self) -> bool:
        """
        Check if queue is full.
        
        Returns:
            True if queue is at maximum capacity
        """
        return self._queue.full()
    
    def clear(self) -> None:
        """Remove all messages from queue."""
        with self._lock:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except Empty:
                    break
    
    def get_all_messages(self) -> List[Any]:
        """
        Get all messages without removing them (for testing).
        
        Returns:
            List of all message data in queue
        """
        messages = []
        temp_messages = []
        
        with self._lock:
            # Extract all messages
            while not self._queue.empty():
                try:
                    msg_wrapper = self._queue.get_nowait()
                    messages.append(deepcopy(msg_wrapper['data']))
                    temp_messages.append(msg_wrapper)
                except Empty:
                    break
            
            # Put them back
            for msg in temp_messages:
                self._queue.put(msg)
        
        return messages
    
    def __len__(self) -> int:
        """
        Get queue length.
        
        Returns:
            Number of messages in queue
        """
        return self.size()
    
    def __iter__(self):
        """
        Iterate over queue messages (non-destructive).
        
        Yields:
            Message data
        """
        for msg in self.get_all_messages():
            yield msg


# Helper Functions

def create_mock_message(
    body: Union[str, dict, bytes],
    message_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    headers: Optional[Dict[str, Any]] = None,
    content_type: str = 'application/json',
    delivery_mode: int = 2,
    priority: int = 0,
    expiration: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a mock message with standard message broker properties.
    
    Args:
        body: Message body (string, dict, or bytes)
        message_id: Unique message identifier
        correlation_id: Correlation ID for request/response patterns
        headers: Custom message headers
        content_type: Message content type
        delivery_mode: Delivery mode (1=non-persistent, 2=persistent)
        priority: Message priority (0-9)
        expiration: Message expiration in milliseconds
        
    Returns:
        Mock message dictionary with metadata
    """
    # Convert body to appropriate format
    if isinstance(body, dict):
        body_str = json.dumps(body)
    elif isinstance(body, bytes):
        body_str = body.decode('utf-8')
    else:
        body_str = str(body)
    
    message = {
        'message_id': message_id or str(uuid.uuid4()),
        'correlation_id': correlation_id,
        'body': body_str,
        'headers': headers or {},
        'content_type': content_type,
        'delivery_mode': delivery_mode,
        'priority': priority,
        'expiration': expiration,
        'timestamp': datetime.now().isoformat(),
        'created_at': time.time()
    }
    
    return message


def track_published_messages(
    mock_channel: Union[MockRabbitMQChannel, MockRedisPublisher],
    filter_by: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Track and filter published messages from mock channel.
    
    Args:
        mock_channel: Mock channel or publisher instance
        filter_by: Optional filter criteria (e.g., {'exchange': 'events', 'routing_key': 'user.*'})
        
    Returns:
        List of published messages matching filter criteria
    """
    messages = mock_channel.get_published_messages()
    
    if filter_by is None:
        return messages
    
    filtered_messages = []
    for msg in messages:
        match = True
        for key, value in filter_by.items():
            if key not in msg:
                match = False
                break
            
            # Support wildcard matching for string values
            if isinstance(value, str) and '*' in value:
                import re
                pattern = value.replace('*', '.*')
                if not re.match(f'^{pattern}$', str(msg[key])):
                    match = False
                    break
            else:
                if msg[key] != value:
                    match = False
                    break
        
        if match:
            filtered_messages.append(msg)
    
    return filtered_messages


def get_queue_depth(
    mock_queue: Union[MockMessageQueue, MockRabbitMQChannel],
    queue_name: Optional[str] = None
) -> int:
    """
    Get the current depth (number of messages) in a queue.
    
    Args:
        mock_queue: MockMessageQueue instance or MockRabbitMQChannel
        queue_name: Queue name (required for MockRabbitMQChannel)
        
    Returns:
        Number of messages in queue
        
    Raises:
        ValueError: If queue_name not provided for MockRabbitMQChannel
        Exception: If queue not found
    """
    if isinstance(mock_queue, MockMessageQueue):
        return mock_queue.size()
    elif isinstance(mock_queue, MockRabbitMQChannel):
        if queue_name is None:
            raise ValueError("queue_name required for MockRabbitMQChannel")
        
        with mock_queue._lock:
            if queue_name not in mock_queue._queues:
                raise Exception(f"Queue '{queue_name}' not found")
            return mock_queue._queues[queue_name].size()
    else:
        raise TypeError(f"Unsupported queue type: {type(mock_queue)}")


# Pytest Fixtures

@pytest.fixture
def mock_rabbitmq():
    """
    Pytest fixture providing a mock RabbitMQ channel.
    
    Provides a fresh MockRabbitMQChannel instance for each test with
    automatic cleanup after test completion.
    
    Usage:
        def test_message_publishing(mock_rabbitmq):
            mock_rabbitmq.queue_declare('test_queue')
            mock_rabbitmq.basic_publish('', 'test_queue', 'Hello World')
            assert mock_rabbitmq.get_published_messages()[0]['body'] == 'Hello World'
    
    Yields:
        MockRabbitMQChannel instance
    """
    channel = MockRabbitMQChannel()
    yield channel
    # Cleanup
    channel.clear_history()


@pytest.fixture
def mock_redis_pubsub():
    """
    Pytest fixture providing a mock Redis pub/sub client.
    
    Provides a fresh MockRedisPublisher instance for each test with
    automatic cleanup after test completion.
    
    Usage:
        def test_message_publishing(mock_redis_pubsub):
            messages = []
            mock_redis_pubsub.subscribe('events', lambda msg: messages.append(msg))
            mock_redis_pubsub.publish('events', {'type': 'user_created'})
            assert len(messages) == 1
    
    Yields:
        MockRedisPublisher instance
    """
    publisher = MockRedisPublisher()
    yield publisher
    # Cleanup
    publisher.clear_history()


@pytest.fixture
def mock_celery():
    """
    Pytest fixture providing a mock Celery task factory.
    
    Provides a factory function that creates MockCeleryTask instances
    for testing asynchronous task execution.
    
    Usage:
        def test_async_task(mock_celery):
            def my_task(x, y):
                return x + y
            
            task = mock_celery(my_task)
            result = task.delay(2, 3)
            assert result.get() == 5
    
    Yields:
        Factory function that creates MockCeleryTask instances
    """
    def create_task(task_func: Optional[Callable] = None, task_id: Optional[str] = None):
        """
        Create a mock Celery task.
        
        Args:
            task_func: Function to execute as task
            task_id: Optional task identifier
            
        Returns:
            MockCeleryTask instance
        """
        return MockCeleryTask(task_func=task_func, task_id=task_id)
    
    yield create_task


# Additional utility fixtures

@pytest.fixture
def mock_message_queue():
    """
    Pytest fixture providing a generic mock message queue.
    
    Provides a fresh MockMessageQueue instance for each test.
    
    Usage:
        def test_queue_operations(mock_message_queue):
            mock_message_queue.enqueue({'data': 'test'})
            message = mock_message_queue.dequeue()
            assert message['data'] == 'test'
    
    Yields:
        MockMessageQueue instance
    """
    queue = MockMessageQueue(maxsize=0)
    yield queue
    # Cleanup
    queue.clear()


@pytest.fixture
def mock_rabbitmq_with_exchanges(mock_rabbitmq):
    """
    Pytest fixture providing a pre-configured RabbitMQ channel with common exchanges.
    
    Sets up typical exchange and queue configurations for testing.
    
    Usage:
        def test_exchange_routing(mock_rabbitmq_with_exchanges):
            channel, config = mock_rabbitmq_with_exchanges
            channel.basic_publish('events', 'user.created', 'test message')
            assert len(channel.get_published_messages()) == 1
    
    Yields:
        Tuple of (MockRabbitMQChannel, exchange_config_dict)
    """
    # Declare common exchanges
    mock_rabbitmq.exchange_declare('events', exchange_type='topic')
    mock_rabbitmq.exchange_declare('tasks', exchange_type='direct')
    mock_rabbitmq.exchange_declare('logs', exchange_type='fanout')
    
    # Declare common queues
    mock_rabbitmq.queue_declare('user_events')
    mock_rabbitmq.queue_declare('email_tasks')
    mock_rabbitmq.queue_declare('system_logs')
    
    # Create bindings
    mock_rabbitmq.queue_bind('user_events', 'events', 'user.*')
    mock_rabbitmq.queue_bind('email_tasks', 'tasks', 'email')
    mock_rabbitmq.queue_bind('system_logs', 'logs')
    
    config = {
        'exchanges': {
            'events': {'type': 'topic', 'queue': 'user_events'},
            'tasks': {'type': 'direct', 'queue': 'email_tasks'},
            'logs': {'type': 'fanout', 'queue': 'system_logs'}
        }
    }
    
    yield mock_rabbitmq, config


@pytest.fixture
def mock_redis_channels(mock_redis_pubsub):
    """
    Pytest fixture providing a pre-configured Redis pub/sub with common channels.
    
    Sets up typical channel configurations for testing.
    
    Usage:
        def test_channel_publishing(mock_redis_channels):
            publisher, channels = mock_redis_channels
            publisher.publish('notifications', 'New notification')
            assert publisher.get_published_messages('notifications')
    
    Yields:
        Tuple of (MockRedisPublisher, channels_list)
    """
    channels = ['notifications', 'events', 'logs', 'metrics']
    
    # Pre-subscribe to channels for testing
    for channel in channels:
        mock_redis_pubsub.subscribe(channel)
    
    yield mock_redis_pubsub, channels


# Message verification helpers for testing

def assert_message_published(
    mock_channel: Union[MockRabbitMQChannel, MockRedisPublisher],
    expected_body: Optional[str] = None,
    expected_count: Optional[int] = None,
    **filters
) -> None:
    """
    Assert that messages were published with expected properties.
    
    Args:
        mock_channel: Mock channel instance
        expected_body: Expected message body (optional)
        expected_count: Expected number of messages (optional)
        **filters: Additional filter criteria
        
    Raises:
        AssertionError: If assertion fails
    """
    messages = mock_channel.get_published_messages()
    
    if expected_count is not None:
        assert len(messages) == expected_count, \
            f"Expected {expected_count} messages, found {len(messages)}"
    
    if expected_body is not None:
        bodies = [msg.get('body') for msg in messages]
        assert expected_body in bodies, \
            f"Expected body '{expected_body}' not found in {bodies}"
    
    for key, value in filters.items():
        for msg in messages:
            if key in msg:
                assert msg[key] == value, \
                    f"Expected {key}={value}, found {msg[key]}"


def assert_queue_depth(
    mock_queue: Union[MockMessageQueue, MockRabbitMQChannel],
    expected_depth: int,
    queue_name: Optional[str] = None
) -> None:
    """
    Assert that queue has expected depth.
    
    Args:
        mock_queue: Mock queue instance
        expected_depth: Expected number of messages
        queue_name: Queue name (for MockRabbitMQChannel)
        
    Raises:
        AssertionError: If depth doesn't match
    """
    actual_depth = get_queue_depth(mock_queue, queue_name)
    assert actual_depth == expected_depth, \
        f"Expected queue depth {expected_depth}, found {actual_depth}"


def assert_task_completed(
    task: MockCeleryTask,
    expected_state: str = MockCeleryTask.SUCCESS,
    expected_result: Optional[Any] = None
) -> None:
    """
    Assert that Celery task completed with expected state and result.
    
    Args:
        task: MockCeleryTask instance
        expected_state: Expected task state
        expected_result: Expected task result (optional)
        
    Raises:
        AssertionError: If task state or result doesn't match
    """
    assert task.state == expected_state, \
        f"Expected task state {expected_state}, found {task.state}"
    
    if expected_result is not None:
        assert task.result == expected_result, \
            f"Expected task result {expected_result}, found {task.result}"
