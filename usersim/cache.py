import collections

class LRUCache:
    """
    Cache Implementation to store recently requested similar users data 
    """
    def __init__(self, capacity):
        """
        capacity defines the number of users to be cached
        """
        self._user_table = collections.OrderedDict()
        self._capacity = capacity
    
    def lookup(self, user_handle):
        """
        Returns the user list from cache if present and move it to front
        """
        if user_handle not in self._user_table:
            return False, None
        similar_users = self._user_table.pop(user_handle)
        self._user_table[user_handle] = similar_users
        return True, similar_users
        
    def insert(self, user_handle, similar_users):
        """
        Insert new user list into cache. 
        Remove the least recently used entry if cache is full
        """
        if user_handle in self._user_table:
            similar_users = self._user_table.pop(user_handle)
        elif self._capacity <= len(self._user_table):
            self._user_table.popitem(last=False)
        self._user_table[user_handle] = similar_users
