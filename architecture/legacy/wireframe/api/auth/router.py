from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from wireframe.db import AsyncSession, get_session

router = APIRouter()
