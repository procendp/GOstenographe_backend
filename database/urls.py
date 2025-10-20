from django.urls import path
from . import views

urlpatterns = [
    path('delete-orders/', views.delete_orders, name='delete-orders'),
    path('get-order-file-counts/', views.get_order_file_counts, name='get-order-file-counts'),
    path('generate-db-order-id/', views.generate_db_order_id, name='generate-db-order-id'),
    path('create-db-order/', views.create_db_order, name='create-db-order'),
    path('delete-uploaded-files/', views.delete_uploaded_files, name='delete-uploaded-files'),
    path('public-delete-uploaded-files/', views.public_delete_uploaded_files, name='public-delete-uploaded-files'),
]
