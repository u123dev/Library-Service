class Session_Mock:
    def __init__(self, *args, **kwargs):
        self.url = "http://test.url"
        self.id = "111"
        self.payment_status = "paid"
