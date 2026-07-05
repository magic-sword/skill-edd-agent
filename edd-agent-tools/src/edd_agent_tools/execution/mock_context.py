class MockSession:
    def __init__(self):
        self.state = {}

class MockInvocationContext:
    def __init__(self):
        self.session = MockSession()
