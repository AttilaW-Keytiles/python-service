
from pydantic import BaseModel, Field
from typing import Optional


class User(BaseModel):

    id: str = Field(
        ...,
        description='Mandatory. Unique ID of the user',
    )
    customer_id: Optional[int] = Field(
        None,
        description='Optional. Link to the Customer table. Later!',
    )
    name: str = Field(
        ..., 
        description='Mandatory. The real name of the user. Can not be empty.'
    )
    email: str = Field(
        ..., description='Mandatory. The name of the user. Can not be empty.'
    )
    username: str = Field(
        ..., 
        description='Mandatory. The username he can log in'
    )
    password: str = Field(
        ..., 
        description='Mandatory. The password as stored in the DB'
    )
    version: int = Field(
        ...,
        description='This is the resource version starts from 1 and automatically incremented by every successful change server side.',
    )
