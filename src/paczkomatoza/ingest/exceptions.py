class CityNotFoundInAPIException(Exception):
    """Wyjątek zgłaszany, gdy API InPost nie zwraca danych dla danego miasta."""
    pass

class CityAlreadyCachedException(Exception):
    """Wyjątek zgłaszany, gdy dane dla danego miasta już istnieją w cache'u."""
    pass