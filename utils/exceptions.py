class RateLimitError(Exception):
    """Exception raised when an API rate limit is exceeded."""
    def __init__(self, source: str, retry_after: int = None):
        self.source = source
        self.retry_after = retry_after
        self.message = f"API Rate Limit Exceeded: The {source} API limit has been reached."
        super().__init__(self.message)
