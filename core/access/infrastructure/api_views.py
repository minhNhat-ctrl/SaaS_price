"""
API Views - JSON endpoints for Access Control (RBAC)

Nguyên tắc:
- Chỉ nhận HttpRequest và trả JsonResponse
- Gọi service layer để xử lý business logic
- Không gọi ORM trực tiếp
- Validate input ở đây
- Handle exceptions từ service

Schema-per-Tenant:
- Access control data lưu trong tenant schema
- Mỗi tenant có riêng roles, permissions, memberships
- Middleware auto-switch schema context
"""
import json
import logging
from functools import wraps
from uuid import UUID
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync

from core.access.domain import (
    MembershipNotFoundError,
    MembershipAlreadyExistsError,
    RoleNotFoundError,
    PermissionDeniedError,
    MembershipStatus,
    RoleType,
)
from core.access.services.access_service import AccessService
from core.access.repositories.access_repo import (
    MembershipRepository,
    RoleRepository,
    PermissionRepository,
    PolicyRepository,
)
from core.access.infrastructure.django_repository import (
    DjangoMembershipRepository,
    DjangoRoleRepository,
    DjangoPermissionRepository,
    DjangoPolicyRepository,
)

logger = logging.getLogger(__name__)


def login_required_api(view_func):
    """
    Decorator to require authentication for API endpoints.
    Returns 401 Unauthorized if user is not authenticated.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_access_service() -> AccessService:
    """Factory function to create AccessService with dependencies"""
    return AccessService(
        membership_repo=DjangoMembershipRepository(),
        role_repo=DjangoRoleRepository(),
        permission_repo=DjangoPermissionRepository(),
        policy_repo=DjangoPolicyRepository(),
    )


def _parse_json_body(request):
    """Parse JSON body từ request"""
    try:
        return json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid JSON body: {str(e)}")


def _membership_to_dict(membership):
    """Convert Membership entity to dict for JSON response"""
    return {
        'id': str(membership.id),
        'user_id': str(membership.user_id),
        'tenant_id': str(membership.tenant_id),
        'email': membership.metadata.get('invited_email', ''),  # Get email from metadata
        'status': membership.status.value,
        'roles': [
            {
                'id': str(r.id),
                'name': r.name,
                'slug': r.slug,
                'type': r.role_type.value,  # Convert enum to string
            }
            for r in membership.roles
        ],
        'invited_by': str(membership.invited_by) if membership.invited_by else None,
        'invited_at': membership.invited_at.isoformat() if membership.invited_at else None,
        'joined_at': membership.joined_at.isoformat() if membership.joined_at else None,  # Changed from activated_at
        'expires_at': membership.expires_at.isoformat() if membership.expires_at else None,
        'created_at': membership.created_at.isoformat() if membership.created_at else None,
        'updated_at': membership.updated_at.isoformat() if membership.updated_at else None,
    }


def _role_to_dict(role):
    """Convert Role entity to dict for JSON response"""
    return {
        'id': str(role.id),
        'name': role.name,
        'slug': role.slug,
        'type': role.type.value,
        'description': role.description,
        'permissions': [
            {
                'id': str(p.id),
                'name': p.name,
                'slug': p.slug,
                'resource': p.resource,
                'action': p.action,
            }
            for p in role.permissions
        ],
    }


# ============================================================
# Membership Endpoints
# ============================================================

@csrf_exempt
@require_http_methods(["GET"])
@login_required_api
def list_memberships_view(request):
    """
    GET /api/access/memberships/ → Danh sách thành viên
    
    Query params:
        tenant_id: UUID của tenant (required)
        status: Lọc theo trạng thái (active, pending, revoked)
    """
    try:
        tenant_id = request.GET.get('tenant_id')
        if not tenant_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameter: tenant_id'
            }, status=400)
        
        service = _get_access_service()
        
        # Parse status filter
        status_param = request.GET.get('status')
        status_filter = None
        if status_param:
            try:
                status_filter = MembershipStatus(status_param)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid status: {status_param}'
                }, status=400)
        
        memberships = async_to_sync(service.get_tenant_members)(
            tenant_id=UUID(tenant_id),
            status=status_filter
        )
        
        return JsonResponse({
            'success': True,
            'memberships': [_membership_to_dict(m) for m in memberships]
        })
        
    except Exception as e:
        logger.error(f"List memberships error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def invite_member_view(request):
    """
    POST /api/access/memberships/invite/ → Mời thành viên mới bằng EMAIL
    
    Body: {
        "tenant_id": "uuid",
        "email": "user@example.com",
        "role_slugs": ["member", "viewer"],
        "expires_at": "2024-12-31T23:59:59Z"  // optional
    }
    
    Note: invited_by lấy từ request.user.id
    """
    try:
        data = _parse_json_body(request)
        
        # Validate required fields
        required_fields = ['tenant_id', 'email', 'role_slugs']
        missing_fields = [f for f in required_fields if not data.get(f)]
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
        
        # Validate email format
        email = data['email'].strip().lower()
        if '@' not in email or '.' not in email.split('@')[1]:
            return JsonResponse({
                'success': False,
                'error': 'Invalid email format'
            }, status=400)
        
        service = _get_access_service()
        
        # Parse expires_at if provided
        expires_at = None
        if data.get('expires_at'):
            try:
                expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid expires_at format (use ISO 8601)'
                }, status=400)
        
        # invited_by = current authenticated user
        from uuid import UUID as ConvertUUID
        try:
            # Django User model uses integer ID, not UUID
            # For now, create a deterministic UUID from user ID
            from uuid import uuid5, NAMESPACE_DNS
            invited_by = uuid5(NAMESPACE_DNS, f"user:{request.user.id}")
            logger.info(f"Invite member by user {request.user.id} (UUID: {invited_by})")
        except (ValueError, AttributeError) as e:
            logger.error(f"Failed to get user ID: {e}, user={request.user}, authenticated={request.user.is_authenticated}")
            return JsonResponse({
                'success': False,
                'error': f'Invalid user session: {str(e)}'
            }, status=401)
        
        membership = async_to_sync(service.invite_member_by_email)(
            tenant_id=UUID(data['tenant_id']),
            email=email,
            role_slugs=data['role_slugs'],
            invited_by=invited_by,
            expires_at=expires_at
        )
        
        return JsonResponse({
            'success': True,
            'membership': _membership_to_dict(membership),
            'message': f'Invitation sent to {email}'
        }, status=201)
        
    except (MembershipAlreadyExistsError, RoleNotFoundError) as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Invite member error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def invite_member_view_old(request):
    """
    POST /api/access/memberships/invite-by-userid/ → Mời thành viên mới (old version - cần user_id)
    
    Body: {
        "user_id": "uuid",
        "tenant_id": "uuid",
        "role_slugs": ["member", "viewer"],
        "invited_by": "uuid",
        "expires_at": "2024-12-31T23:59:59Z"  // optional
    }
    """
    try:
        data = _parse_json_body(request)
        
        # Validate required fields
        required_fields = ['user_id', 'tenant_id', 'role_slugs', 'invited_by']
        missing_fields = [f for f in required_fields if not data.get(f)]
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
        
        service = _get_access_service()
        
        # Parse expires_at if provided
        expires_at = None
        if data.get('expires_at'):
            try:
                expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid expires_at format (use ISO 8601)'
                }, status=400)
        
        membership = async_to_sync(service.invite_member)(
            user_id=UUID(data['user_id']),
            tenant_id=UUID(data['tenant_id']),
            role_slugs=data['role_slugs'],
            invited_by=UUID(data['invited_by']),
            expires_at=expires_at
        )
        
        return JsonResponse({
            'success': True,
            'membership': _membership_to_dict(membership),
            'message': 'Member invited successfully'
        }, status=201)
        
    except (MembershipAlreadyExistsError, RoleNotFoundError) as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Invite member error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def activate_membership_view(request, membership_id):
    """POST /api/access/memberships/<membership_id>/activate/ → Kích hoạt membership"""
    try:
        service = _get_access_service()
        # membership_id is already UUID from URL converter
        if not isinstance(membership_id, UUID):
            membership_id = UUID(membership_id)
        membership = async_to_sync(service.activate_membership)(membership_id)
        
        return JsonResponse({
            'success': True,
            'membership': _membership_to_dict(membership)
        })
        
    except MembershipNotFoundError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=404)
    except Exception as e:
        logger.error(f"Activate membership error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def revoke_membership_view(request, membership_id):
    """POST /api/access/memberships/<membership_id>/revoke/ → Thu hồi membership"""
    try:
        logger.info(f"[REVOKE_MEMBERSHIP] Request for membership_id: {membership_id}")
        service = _get_access_service()
        
        # membership_id is already UUID from URL converter, don't convert again
        if not isinstance(membership_id, UUID):
            membership_id = UUID(membership_id)
        
        # revoke_membership returns bool, not Membership object
        success = async_to_sync(service.revoke_membership)(membership_id)
        
        if success:
            logger.info(f"[REVOKE_MEMBERSHIP] Successfully revoked membership: {membership_id}")
            return JsonResponse({
                'success': True,
                'message': 'Membership revoked successfully'
            })
        else:
            logger.warning(f"[REVOKE_MEMBERSHIP] Failed to revoke membership: {membership_id}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to revoke membership'
            }, status=500)
        
        if success:
            logger.info(f"[REVOKE_MEMBERSHIP] Successfully revoked membership: {membership_id}")
            return JsonResponse({
                'success': True,
                'message': 'Membership revoked successfully'
            })
        else:
            logger.warning(f"[REVOKE_MEMBERSHIP] Failed to revoke membership: {membership_id}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to revoke membership'
            }, status=500)
        
    except MembershipNotFoundError as e:
        logger.error(f"[REVOKE_MEMBERSHIP] Membership not found: {membership_id}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=404)
    except ValueError as e:
        logger.error(f"[REVOKE_MEMBERSHIP] Invalid UUID: {membership_id}")
        return JsonResponse({
            'success': False,
            'error': f'Invalid membership ID format: {str(e)}'
        }, status=400)
    except Exception as e:
        logger.error(f"[REVOKE_MEMBERSHIP] Unexpected error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def assign_roles_view(request, membership_id):
    """
    POST /api/access/memberships/<membership_id>/assign-roles/ → Gán roles
    
    Body: {
        "role_slugs": ["admin", "editor"]
    }
    """
    try:
        data = _parse_json_body(request)
        
        if not data.get('role_slugs'):
            return JsonResponse({
                'success': False,
                'error': 'Missing required field: role_slugs'
            }, status=400)
        
        service = _get_access_service()
        # membership_id is already UUID from URL converter
        if not isinstance(membership_id, UUID):
            membership_id = UUID(membership_id)
        membership = async_to_sync(service.assign_roles_to_membership)(
            membership_id=membership_id,
            role_slugs=data['role_slugs']
        )
        
        return JsonResponse({
            'success': True,
            'membership': _membership_to_dict(membership)
        })
        
    except (MembershipNotFoundError, RoleNotFoundError) as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=404)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Assign roles error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============================================================
# Role Endpoints
# ============================================================

@csrf_exempt
@require_http_methods(["GET"])
@login_required_api
def list_roles_view(request):
    """
    GET /api/access/roles/ → Danh sách roles
    
    Query params:
        tenant_id: UUID của tenant (required)
        type: Lọc theo loại (system, custom, predefined)
    """
    try:
        tenant_id = request.GET.get('tenant_id')
        if not tenant_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameter: tenant_id'
            }, status=400)
        
        service = _get_access_service()
        
        # Parse type filter
        type_param = request.GET.get('type')
        type_filter = None
        if type_param:
            try:
                type_filter = RoleType(type_param)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid type: {type_param}'
                }, status=400)
        
        roles = async_to_sync(service.list_roles_by_tenant)(
            tenant_id=UUID(tenant_id),
            role_type=type_filter
        )
        
        return JsonResponse({
            'success': True,
            'roles': [_role_to_dict(r) for r in roles]
        })
        
    except Exception as e:
        logger.error(f"List roles error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def create_custom_role_view(request):
    """
    POST /api/access/roles/ → Tạo custom role
    
    Body: {
        "tenant_id": "uuid",
        "name": "Custom Role",
        "slug": "custom-role",
        "description": "Description",
        "permission_slugs": ["read:products", "write:products"]
    }
    """
    try:
        data = _parse_json_body(request)
        
        # Validate required fields
        required_fields = ['tenant_id', 'name', 'slug', 'permission_slugs']
        missing_fields = [f for f in required_fields if not data.get(f)]
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
        
        service = _get_access_service()
        
        role = async_to_sync(service.create_custom_role)(
            tenant_id=UUID(data['tenant_id']),
            name=data['name'],
            slug=data['slug'],
            description=data.get('description', ''),
            permission_slugs=data['permission_slugs']
        )
        
        return JsonResponse({
            'success': True,
            'role': _role_to_dict(role),
            'message': 'Role created successfully'
        }, status=201)
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Create role error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }, status=500)


# ============================================================
# Permission Check Endpoints
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def check_permission_view(request):
    """
    POST /api/access/check-permission/ → Kiểm tra quyền
    
    Body: {
        "user_id": "uuid",
        "tenant_id": "uuid",
        "permission_slug": "read:products"
    }
    
    Returns: {
        "success": true,
        "has_permission": true/false
    }
    """
    try:
        data = _parse_json_body(request)
        
        # Validate required fields
        required_fields = ['user_id', 'tenant_id', 'permission_slug']
        missing_fields = [f for f in required_fields if not data.get(f)]
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
        
        service = _get_access_service()
        
        has_permission = async_to_sync(service.check_permission)(
            user_id=UUID(data['user_id']),
            tenant_id=UUID(data['tenant_id']),
            permission_slug=data['permission_slug']
        )
        
        return JsonResponse({
            'success': True,
            'has_permission': has_permission
        })
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Check permission error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
