"""Demo 依赖：简化用户与权限检查"""
from fastapi import HTTPException, status, Depends
from pydantic import BaseModel

class DemoUser(BaseModel):
    username: str
    permissions: set[str]


def get_current_user():
    """示例当前用户，默认拥有所有 demo 权限"""
    return DemoUser(username="demo", permissions={"demo:read", "demo:write"})


def require_permission(permission: str):
    """权限校验依赖"""
    def _checker(user: DemoUser = Depends(get_current_user)):
        if permission not in user.permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
        return user
    return _checker
