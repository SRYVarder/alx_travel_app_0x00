from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Listing, Booking, Review


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class ListingSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()
    total_price_for_nights = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'id', 'title', 'description', 'property_type', 'price_per_night',
            'bedrooms', 'bathrooms', 'max_guests', 'location', 'is_available',
            'owner', 'created_at', 'updated_at', 'image_url', 'average_rating',
            'total_reviews', 'total_price_for_nights'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']

    def get_image_url(self, obj):
        """Get the full URL for the listing image"""
        if hasattr(obj, 'image') and obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
        return None

    def get_average_rating(self, obj):
        """Calculate average rating from reviews"""
        reviews = obj.reviews.all()
        if reviews.exists():
            return sum(review.rating for review in reviews) / reviews.count()
        return 0

    def get_total_reviews(self, obj):
        """Get total number of reviews"""
        return obj.reviews.count()

    def get_total_price_for_nights(self, obj):
        """Calculate total price for 7 nights (default)"""
        request = self.context.get('request')
        nights = request.query_params.get('nights', 7)
        try:
            nights = int(nights)
            return obj.total_price_for_nights(nights)
        except (ValueError, TypeError):
            return obj.total_price_for_nights(7)


class BookingSerializer(serializers.ModelSerializer):
    listing = ListingSerializer(read_only=True)
    listing_id = serializers.IntegerField(write_only=True)
    guest = UserSerializer(read_only=True)
    nights_booked = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'listing', 'listing_id', 'guest', 'check_in_date',
            'check_out_date', 'total_price', 'status', 'created_at',
            'nights_booked'
        ]
        read_only_fields = ['guest', 'total_price', 'created_at', 'nights_booked']

    def validate(self, data):
        """Validate booking data"""
        listing_id = data.get('listing_id')
        check_in_date = data.get('check_in_date')
        check_out_date = data.get('check_out_date')
        
        if listing_id and check_in_date and check_out_date:
            # Check for overlapping bookings
            overlapping_bookings = Booking.objects.filter(
                listing_id=listing_id,
                status__in=['confirmed', 'pending'],
                check_in_date__lt=check_out_date,
                check_out_date__gt=check_in_date
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if overlapping_bookings.exists():
                raise serializers.ValidationError(
                    "This listing is not available for the selected dates."
                )
            
            # Check if listing is available
            listing = Listing.objects.filter(id=listing_id, is_available=True).first()
            if not listing:
                raise serializers.ValidationError("This listing is not available.")
        
        return data

    def create(self, validated_data):
        """Create booking with calculated total price"""
        listing_id = validated_data.pop('listing_id')
        listing = Listing.objects.get(id=listing_id)
        
        nights = (validated_data['check_out_date'] - validated_data['check_in_date']).days
        total_price = listing.total_price_for_nights(nights)
        
        validated_data['total_price'] = total_price
        
        return super().create(validated_data)

    def get_nights_booked(self, obj):
        """Get number of nights booked"""
        return obj.nights_booked()


class ReviewSerializer(serializers.ModelSerializer):
    listing = ListingSerializer(read_only=True)
    listing_id = serializers.IntegerField(write_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'listing', 'listing_id', 'user', 'rating', 
            'comment', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

    def validate(self, data):
        """Validate review data"""
        listing_id = data.get('listing_id')
        user = self.context['request'].user
        
        # Prevent multiple reviews from the same user for the same listing
        if listing_id and Review.objects.filter(
            listing_id=listing_id, 
            user=user
        ).exists():
            raise serializers.ValidationError(
                "You have already reviewed this listing."
            )
        
        return data

    def create(self, validated_data):
        """Create review with current user"""
        listing_id = validated_data.pop('listing_id')
        validated_data['user'] = self.context['request'].user
        validated_data['listing_id'] = listing_id
        
        return super().create(validated_data)
