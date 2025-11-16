
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.db.models import Sum, Count
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.contrib import messages
from django.db import transaction
from datetime import datetime, timedelta
import random
import string
from .models import (
    UserProfile, 
    AirtimeTransaction,
    DataTransaction,
    EPIN,
    CableSubscription,
    Transaction,
    Wallet,
    ServiceProvider,
    DataPlan,
    CablePackage
)

# Custom admin site with enhanced UI
class VTUAdminSite(AdminSite):
    site_header = 'VTU Platform Administration'
    site_title = 'VTU Admin Portal'
    index_title = 'Welcome to VTU Admin'
    
    def get_app_list(self, request):
        app_list = super().get_app_list(request)
        # Add custom dashboard link
        app_list.append({
            'name': 'Reports Dashboard',
            'app_label': 'reports',
            'models': [{
                'name': 'View Reports',
                'admin_url': '/admin/reports/',
                'view_only': True
            }]
        })
        return app_list

vtu_admin_site = VTUAdminSite(name='vtu_admin')

# ======================= UTILITY FUNCTIONS =======================
def generate_random_pin(length=12):
    """Generate random EPIN"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_last_30_days():
    """Get date range for last 30 days"""
    today = datetime.now().date()
    return [today - timedelta(days=i) for i in range(30)]

# ======================= INLINE ADMIN CLASSES =======================
class WalletInline(admin.StackedInline):
    model = Wallet
    can_delete = False
    verbose_name_plural = 'Wallet'
    readonly_fields = ('balance', 'last_updated')
    extra = 0

class TransactionInline(admin.TabularInline):
    model = Transaction
    extra = 0
    readonly_fields = ('transaction_id', 'amount', 'transaction_type', 'status', 'created_at')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

# ======================= MAIN ADMIN CLASSES =======================
@admin.register(UserProfile, site=vtu_admin_site)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'account_balance', 'is_verified', 'user_actions')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('user__username', 'phone_number')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [WalletInline, TransactionInline]
    actions = ['verify_users', 'unverify_users']
    
    def account_balance(self, obj):
        return f"₦{obj.wallet.balance:,.2f}"
    account_balance.short_description = 'Balance'
    
    def user_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Transactions</a>&nbsp;'
            '<a class="button" href="{}">Fund Wallet</a>',
            reverse('admin:vtu_app_transaction_changelist') + f'?user__id__exact={obj.user.id}',
            reverse('admin:fund_wallet', args=[obj.id])
        )
    user_actions.short_description = 'Actions'
    user_actions.allow_tags = True
    
    def verify_users(self, request, queryset):
        queryset.update(is_verified=True)
    verify_users.short_description = "Verify selected users"
    
    def unverify_users(self, request, queryset):
        queryset.update(is_verified=False)
    unverify_users.short_description = "Unverify selected users"
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<path:user_id>/fund-wallet/', self.admin_site.admin_view(self.fund_wallet_view), name='fund_wallet'),
        ]
        return custom_urls + urls
    
    def fund_wallet_view(self, request, user_id, *args, **kwargs):
        if request.method == 'POST':
            try:
                amount = float(request.POST.get('amount'))
                user_profile = UserProfile.objects.get(id=user_id)
                wallet = user_profile.wallet
                wallet.balance += amount
                wallet.save()
                
                # Create transaction record
                Transaction.objects.create(
                    user=user_profile.user,
                    amount=amount,
                    transaction_type='wallet_funding',
                    status='successful',
                    description=f'Admin wallet funding: ₦{amount:,.2f}'
                )
                
                messages.success(request, f'Successfully funded wallet with ₦{amount:,.2f}')
                return HttpResponseRedirect(reverse('admin:vtu_app_userprofile_change', args=[user_id]))
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        
        context = {
            **self.admin_site.each_context(request),
            'user_id': user_id,
            'opts': self.model._meta,
            'title': 'Fund User Wallet'
        }
        return render(request, 'admin/fund_wallet.html', context)

@admin.register(ServiceProvider, site=vtu_admin_site)
class ServiceProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'service_type', 'is_active', 'total_transactions')
    list_filter = ('service_type', 'is_active')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    actions = ['activate_providers', 'deactivate_providers']
    
    def total_transactions(self, obj):
        return Transaction.objects.filter(
            service_provider=obj
        ).count()
    total_transactions.short_description = 'Transactions'
    
    def activate_providers(self, request, queryset):
        queryset.update(is_active=True)
    activate_providers.short_description = "Activate selected providers"
    
    def deactivate_providers(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_providers.short_description = "Deactivate selected providers"

@admin.register(DataPlan, site=vtu_admin_site)
class DataPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'amount', 'data_volume', 'validity_days', 'is_active')
    list_filter = ('provider', 'is_active')
    search_fields = ('name', 'provider__name')
    list_editable = ('amount', 'is_active')
    actions = ['activate_plans', 'deactivate_plans']
    
    def activate_plans(self, request, queryset):
        queryset.update(is_active=True)
    activate_plans.short_description = "Activate selected plans"
    
    def deactivate_plans(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_plans.short_description = "Deactivate selected plans"

@admin.register(AirtimeTransaction, site=vtu_admin_site)
class AirtimeTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'network', 'phone_number', 'amount', 'status', 'created_at', 'admin_actions')
    list_filter = ('status', 'network', 'created_at')
    search_fields = ('transaction_id', 'user__username', 'phone_number')
    readonly_fields = ('transaction_id', 'created_at')
    actions = ['mark_as_successful', 'mark_as_failed', 'retry_failed_transactions']
    
    def admin_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">View</a>&nbsp;'
            '<a class="button" href="{}">Retry</a>',
            reverse('admin:vtu_app_airtimetransaction_change', args=[obj.id]),
            reverse('admin:retry_airtime', args=[obj.id])
        )
    admin_actions.short_description = 'Actions'
    
    def mark_as_successful(self, request, queryset):
        queryset.update(status='successful')
    mark_as_successful.short_description = "Mark selected as successful"
    
    def mark_as_failed(self, request, queryset):
        queryset.update(status='failed')
    mark_as_failed.short_description = "Mark sel
