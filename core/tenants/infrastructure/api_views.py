"""
API Views - JSON endpoints for Tenant Management

Nguyên tắc:
- Chỉ nhận HttpRequest và trả JsonResponse
- Gọi service layer để xử lý business logic
- Không gọi ORM trực tiếp
- Validate input ở đây
- Handle exceptions từ service

Schema-per-Tenant:
- Mỗi tenant có riêng PostgreSQL schema
- django-tenants auto-create schema khi tạo tenant
- Queries tự động filter theo schema context
"""
import json
import logging
from functools import wraps
from uuid import UUID
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync

from core.tenants.domain import (
    TenantNotFoundError,
    TenantAlreadyExistsError,
    InvalidTenantSlugError,
    TenantStatus,
)
from core.tenants.services.tenant_service import TenantService
from core.tenants.infrastructure.django_repository import DjangoTenantRepository

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


def _get_tenant_service() -> TenantService:
    """Factory function to create TenantService with dependencies"""
    repository = DjangoTenantRepository()
    return TenantService(repository)


def _parse_json_body(request):
    """Parse JSON body từ request"""
    try:
        return json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid JSON body: {str(e)}")


def _tenant_to_dict(tenant):
    """Convert Tenant entity to dict for JSON response"""
    return {
        'id': str(tenant.id),
        'name': tenant.name,
        'slug': tenant.slug,
        'schema_name': tenant.schema_name,
        'status': tenant.status.value,
        'domains': [
            {
                'domain': d.domain,
                'is_primary': d.is_primary,
            }
            for d in tenant.domains
        ],
        'created_at': tenant.created_at.isoformat() if tenant.created_at else None,
        'updated_at': tenant.updated_at.isoformat() if tenant.updated_at else None,
    }


@csrf_exempt
@require_http_methods(["GET"])
@login_required_api
def list_tenants_view(request):
    """
    GET /api/tenants/ → Danh sách tenant mà user có quyền truy cập
    
    ⚠️ SECURITY: Chỉ trả về tenants mà user có membership
    """
    try:
        service = _get_tenant_service()
        
        # Parse status filter
        status_param = request.GET.get('status')
        status_filter = None
        if status_param:
            try:
                status_filter = TenantStatus(status_param)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid status: {status_param}'
                }, status=400)
        
        # Get user ID
        from uuid import uuid5, NAMESPACE_DNS
        user_uuid = uuid5(NAMESPACE_DNS, f"user:{request.user.id}")
        
        # Get tenants for this user only (SECURITY FIX)
        tenants = async_to_sync(service.list_tenants_by_user)(
            user_id=user_uuid,
            status=status_filter
        )
        
        logger.info(f"User {request.user.id} accessed {len(tenants)} tenants")
        
        return JsonResponse({
            'success': True,
            'tenants': [_tenant_to_dict(t) for t in tenants]
        })
        
    except Exception as e:
        logger.error(f"List tenants error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def create_tenant_view(request):
    """
    POST /api/tenants/ → Tạo tenant mới (auto-create schema)
    
    SECURITY: Tự động tạo membership với role "admin" cho user tạo tenant
    """
    try:
        data = _parse_json_body(request)
        
        # Validate required fields
        required_fields = ['name', 'slug', 'domain']
        missing_fields = [f for f in required_fields if not data.get(f)]
        if missing_fields:
            return JsonResponse({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=400)
        
        service = _get_tenant_service()
        
        # Create tenant (auto-create schema via django-tenants)
        tenant = async_to_sync(service.create_tenant)(
            name=data['name'],
            slug=data['slug'],
            domain=data['domain'],
            is_primary=True
        )
        
        # SECURITY FIX: Auto-create membership for creator with admin role
        try:
            from uuid import uuid5, NAMESPACE_DNS
            from core.access.services.access_service import AccessService
            from core.access.infrastructure.django_repository import (
                DjangoMembershipRepository,
                DjangoRoleRepository,
                DjangoPermissionRepository,
                DjangoPolicyRepository,
            )
            
            user_uuid = uuid5(NAMESPACE_DNS, f"user:{request.user.id}")
            
            access_service = AccessService(
                membership_repo=DjangoMembershipRepository(),
                role_repo=DjangoRoleRepository(),
                permission_repo=DjangoPermissionRepository(),
                policy_repo=DjangoPolicyRepository(),
            )
            
            # Create membership with admin role for tenant creator
            membership = async_to_sync(access_service.invite_member)(
                user_id=user_uuid,
                tenant_id=tenant.id,
                role_slugs=['admin'],  # Creator gets admin role
                invited_by=user_uuid,  # Self-invited
            )
            
            # Activate immediately (no need to accept invitation)
            async_to_sync(access_service.activate_membership)(membership.id)
            
            logger.info(f"Created tenant {tenant.id} with admin membership for user {request.user.id}")
            
        except Exception as e:
            logger.error(f"Failed to create membership for new tenant: {e}")
            # Don't fail the whole request, tenant was created successfully
        
        return JsonResponse({
            'success': True,
            'tenant': _tenant_to_dict(tenant),
            'message': 'Tenant created successfully'
        }, status=201)
        
    except (InvalidTenantSlugError, TenantAlreadyExistsError) as e:
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
        logger.error(f"Create tenant error: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Internal error: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
@login_required_api
def get_tenant_view(request, tenant_id):
    """GET /api/tenants/<tenant_id>/ → Lấy thông tin tenant"""
    try:
        service = _get_tenant_service()
        # tenant_id from URL is already UUID object (converted by Django)
        if not isinstance(tenant_id, UUID):
            tenant_id = UUID(tenant_id)
        tenant = async_to_sync(service.get_tenant_by_id)(tenant_id)
        
        return JsonResponse({
            'success': True,
            'tenant': _tenant_to_dict(tenant)
        })
        
    except TenantNotFoundError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=404)
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid tenant ID format'
        }, status=400)
    except Exception as e:
        logger.error(f"Get tenant error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["PATCH", "PUT"])
@login_required_api
def update_tenant_view(request, tenant_id):
    """PATCH/PUT /api/tenants/<tenant_id>/ → Cập nhật tenant"""
    try:
        data = _parse_json_body(request)
        service = _get_tenant_service()
        
        if not isinstance(tenant_id, UUID):
            tenant_id = UUID(tenant_id)
        
        tenant = async_to_sync(service.update_tenant_info)(
            tenant_id=tenant_id,
            name=data.get('name')
        )
        
        return JsonResponse({
            'success': True,
            'tenant': _tenant_to_dict(tenant)
        })
        
    except TenantNotFoundError as e:
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
        logger.error(f"Update tenant error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def activate_tenant_view(request, tenant_id):
    """POST /api/tenants/<tenant_id>/activate/ → Activate tenant"""
    try:
        service = _get_tenant_service()
        if not isinstance(tenant_id, UUID):
            tenant_id = UUID(tenant_id)
        tenant = async_to_sync(service.activate_tenant)(tenant_id)
        
        return JsonResponse({
            'success': True,
            'tenant': _tenant_to_dict(tenant)
        })
        
    except TenantNotFoundError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=404)
    except Exception as e:
        logger.error(f"Activate tenant error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def suspend_tenant_view(request, tenant_id):
    """POST /api/tenants/<tenant_id>/suspend/ → Suspend tenant"""
    try:
        service = _get_tenant_service()
        if not isinstance(tenant_id, UUID):
            tenant_id = UUID(tenant_id)
        tenant = async_to_sync(service.suspend_tenant)(tenant_id)
        
        return JsonResponse({
            'success': True,
            'tenant': _tenant_to_dict(tenant)
        })
        
    except TenantNotFoundError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=404)
    except Exception as e:
        logger.error(f"Suspend tenant error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
@login_required_api
def delete_tenant_view(request, tenant_id):
    """DELETE /api/tenants/<tenant_id>/ → Xóa tenant (soft delete)"""
    try:
        service = _get_tenant_service()
        if not isinstance(tenant_id, UUID):
            tenant_id = UUID(tenant_id)
        success = async_to_sync(service.delete_tenant)(tenant_id)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'Tenant deleted successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to delete tenant'
            }, status=400)
        
    except TenantNotFoundError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=404)
    except Exception as e:
        logger.error(f"Delete tenant error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required_api
def add_domain_view(request, tenant_id):
    """POST /api/tenants/<tenant_id>/add-domain/ → Thêm domain mới"""
    try:
        data = _parse_json_body(request)
        
        if not data.get('domain'):
            return JsonResponse({
                'success': False,
                'error': 'Missing required field: domain'
            }, status=400)
        
        service = _get_tenant_service()
        if not isinstance(tenant_id, UUID):
            tenant_id = UUID(tenant_id)
        tenant = async_to_sync(service.add_domain_to_tenant)(
            tenant_id=tenant_id,
            domain=data['domain'],
            is_primary=data.get('is_primary', False)
        )
        
        return JsonResponse({
            'success': True,
            'tenant': _tenant_to_dict(tenant)
        })
        
    except TenantNotFoundError as e:
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
        logger.error(f"Add domain error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# ============================================================
# Combined Views (to handle multiple methods on same path)
# ============================================================

@csrf_exempt
def tenants_list_create_view(request):
    """
    Combined view for list and create
    GET /api/tenants/ → List tenants
    POST /api/tenants/ → Create tenant
    """
    if request.method == 'GET':
        return list_tenants_view(request)
    elif request.method == 'POST':
        return create_tenant_view(request)
    else:
        return JsonResponse({
            'success': False,
            'error': 'Method not allowed'
        }, status=405)


@csrf_exempt
def tenant_detail_view(request, tenant_id):
    """
    Combined view for get, update, delete
    GET /api/tenants/<id>/ → Get tenant
    PATCH/PUT /api/tenants/<id>/ → Update tenant
    DELETE /api/tenants/<id>/ → Delete tenant
    """
    if request.method == 'GET':
        return get_tenant_view(request, tenant_id)
    elif request.method in ['PATCH', 'PUT']:
        return update_tenant_view(request, tenant_id)
    elif request.method == 'DELETE':
        return delete_tenant_view(request, tenant_id)
    else:
        return JsonResponse({
            'success': False,
            'error': 'Method not allowed'
        }, status=405)

