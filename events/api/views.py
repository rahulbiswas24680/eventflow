from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from drf_spectacular.utils import extend_schema
from rest_framework import filters, generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from events.models import RSVP, Event

from ..models import RSVP, Event, EventImage, TicketType
from .serializers import (EventDetailSerializer, EventSerializer,
                          RSVPSerializer, TicketTypeSerializer)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'



class EventListCreateView(generics.ListCreateAPIView):
    queryset = Event.objects.all().order_by("created_at")
    serializer_class = EventSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'location', 'date']


class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Event.objects.all()
    serializer_class = EventDetailSerializer


class TicketTypeListCreateView(generics.ListCreateAPIView):
    queryset = TicketType.objects.all().order_by("created_at")
    serializer_class = TicketTypeSerializer


class TicketTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TicketType.objects.all()
    serializer_class = TicketTypeSerializer


@extend_schema(
    summary="List all the users of each event.",
    description="Return a list of all user details of each event.",
)
class RSVPListCreateView(generics.ListCreateAPIView):
    queryset = RSVP.objects.all()
    serializer_class = RSVPSerializer
    filter_backends = [filters.SearchFilter]
    pagination_class = StandardResultsSetPagination
    search_fields = ['attendee__username', 'attendee__email']

    def get_queryset(self):
        queryset = super().get_queryset().filter(attendee=self.request.user)
        event_id = self.request.query_params.get("event")
        status = self.request.query_params.get("status")
        ticket = self.request.query_params.get("ticket")

        if event_id:
            queryset = queryset.filter(event_id=event_id)

        # 🧩 Filter by status
        if status == "attended":
            queryset = queryset.filter(is_attended=True)
        elif status == "registered":
            queryset = queryset.filter(is_attended=False)
        elif status == "cancelled":
            queryset = queryset.filter(is_cancelled=True)
        
        if ticket:
            queryset = queryset.filter(transaction__ticket_type__id=ticket)
        print(queryset)
        return queryset.order_by("created_at")
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)

        # 🧮 Calculate stats
        total_registered = queryset.count()
        attended_count = queryset.filter(is_attended=True).count()
        pending_count = queryset.filter(is_attended=False, is_cancelled=False).count()
        attendance_rate = (
            round((attended_count / total_registered) * 100, 2)
            if total_registered > 0
            else 0
        )

        stats = {
            "total_registered": total_registered,
            "attended_count": attended_count,
            "pending_count": pending_count,
            "attendance_rate": attendance_rate,
        }

        # ✅ Combine paginated results + stats
        paginated_response = self.get_paginated_response(serializer.data)
        paginated_response.data["stats"] = stats
        return paginated_response


class RSVPDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RSVP.objects.all()
    serializer_class = RSVPSerializer


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_rsvp_status(request, rsvp_id):
    """
    PATCH API to update RSVP status
    """
    try:
        rsvp = get_object_or_404(RSVP, id=rsvp_id)
        
        # Check if user is the organizer of the event
        if request.user != rsvp.event.organizer.user:
            return Response(
                {"error": "You don't have permission to update this RSVP."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        action = request.data.get('action')
        
        if action == 'mark_attended':
            rsvp.is_attended = True
            rsvp.is_completed = True
            rsvp.is_active = False
        elif action == 'mark_unattended':
            rsvp.is_attended = False
            rsvp.is_completed = False
            rsvp.is_active = True
        elif action == 'cancel':
            rsvp.is_cancelled = True
            rsvp.is_active = False
            rsvp.is_completed = False
        elif action == 'remove':
            # Completely remove the RSVP
            rsvp.delete()
            return Response(
                {"message": "RSVP removed successfully."},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Invalid action."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save changes if not removing
        if action != 'remove':
            rsvp.save()
            
        serializer = RSVPSerializer(rsvp)
        return Response({
            "message": f"RSVP updated successfully.",
            "rsvp": serializer.data
        }, status=status.HTTP_200_OK)
        
    except RSVP.DoesNotExist:
        return Response(
            {"error": "RSVP not found."},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

@login_required
@require_http_methods(["DELETE"])
def delete_event_image(request, event_id, image_id):
    event = get_object_or_404(Event, id=event_id, organizer__user=request.user)
    image = get_object_or_404(EventImage, id=image_id, event=event)
    image.image.delete(save=False)  # delete file from storage
    image.delete()
    return JsonResponse({"success": True, "message": "Event image deleted successfully"})


@login_required
@require_http_methods(["DELETE"])
def delete_ticket_image(request, event_id, ticket_id):
    event = get_object_or_404(Event, id=event_id, organizer__user=request.user)
    ticket_img = get_object_or_404(TicketType, id=ticket_id, event=event)
    ticket_img.image = None
    ticket_img.save(update_fields=["image"])
    return JsonResponse({"success": True, "message": "Ticket image deleted successfully"})

