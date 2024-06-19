

def detail_borrowing_info(instance):
    return (f"Borrowing id: {instance.id}\n"
            f"Book: {instance.book}\n"
            f"User: {instance.user}\n"
            f"Date: {instance.borrow_date}\n"
            f"Expected Return: {instance.expected_return_date}")
