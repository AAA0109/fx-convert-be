from dataclasses import dataclass
from typing import Optional

from main.apps.corpay.services.api.dataclasses.base import JsonDictMixin


@dataclass
class ListCustomersParams(JsonDictMixin):
    """
    This field accepts the business registration number of corporate customer.
    """
    businessRegistrationNumber: Optional[str] = None
    """
    This field accepts the type of customer. (INDIVIDUAL, CORPORATE)
    """
    customerType: Optional[str] = None
    """
    This field accepts the email ID of the customer.
    """
    email: Optional[str] = None
    """
    This field accepts the mobile number of a customer without the country code.
    """
    mobile: Optional[str] = None
    """
    This field accepts the order which can be ASC or DESC.
    """
    order: Optional[str] = None
    """
    This field accepts the page number to be returned. The acceptable values are 0-N.
    This field works with size field such that total number of records/size of each page = number of pages(N).
    This field can then give a particular page.
    """
    page: Optional[int] = 0
    """
    This field contains the unique parent customer identifier generated at the time of customer creation.
    """
    parentCustomerHashId: Optional[str] = None
    """
    This field accepts the number of elements per page.
    """
    size: Optional[int] = 100
    """
    This parameter can filter the customers, based on the exact value of tagKey defined against customers.
    This can be used as an independent search parameter.
    """
    tagKey: Optional[str] = None
    """
    This parameter can filter the customers, based on the approximating value of tagValue
    (that may be mapped for a tagKey defined against customers).
    This can be used as an independent search parameter.
    """
    tagValue: Optional[str] = None
