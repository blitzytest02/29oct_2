"""
User model stub for test purposes.
This is a minimal placeholder to allow test mocking to work.
"""


class Query:
    """Stub Query class for mocking."""
    
    @staticmethod
    def get(user_id):
        """Stub get method."""
        pass
    
    @staticmethod
    def filter_by(**kwargs):
        """Stub filter_by method."""
        return Query()
    
    @staticmethod
    def first():
        """Stub first method."""
        pass


class User:
    """Stub User model class for testing."""
    
    query = Query()
    
    def __init__(self):
        self.id = None
        self.email = None
        self.is_active = True
        self.roles = []
        self.permissions = []
