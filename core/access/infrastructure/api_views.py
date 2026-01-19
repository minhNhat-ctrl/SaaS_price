"""
API Views - JSON endpoints for Access Control (RBAC)
"""Legacy import shim for Access API views."""

from core.access.api.views import *  # noqa: F401,F403
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
