class Session_Mock:
    def __init__(self, *args, **kwargs):
        self.url = "http://test.url"
        self.id = "111"
        self.payment_status = "paid"


class Session_Mock_not_paid:
    def __init__(self, *args, **kwargs):
        self.url = "http://test.url"
        self.id = "333"
        self.payment_status = ""


class Session_Mock_expired:
    def __init__(self, *args, **kwargs):
        self.url = "http://test.url"
        self.id = "333"
        self.payment_status = ""
        self.status = "expired"
