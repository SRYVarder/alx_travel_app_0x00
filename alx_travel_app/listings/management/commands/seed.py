import random
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from faker import Faker
from ...models import Listing, Booking, Review

fake = Faker()

class Command(BaseCommand):
    help = 'Seed the database with sample travel listings data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=5,
            help='Number of users to create (default: 5)',
        )
        parser.add_argument(
            '--listings',
            type=int,
            default=20,
            help='Number of listings to create (default: 20)',
        )
        parser.add_argument(
            '--bookings',
            type=int,
            default=30,
            help='Number of bookings to create (default: 30)',
        )
        parser.add_argument(
            '--reviews',
            type=int,
            default=25,
            help='Number of reviews to create (default: 25)',
        )

    def handle(self, *args, **options):
        self.stdout.write('🚀 Starting database seeding...')
        self.stdout.write(self.style.WARNING('This will create sample data. Continue?'))
        
        # Create sample users
        self._create_users(options['users'])
        
        # Create sample listings
        self._create_listings(options['listings'])
        
        # Create sample bookings
        self._create_bookings(options['bookings'])
        
        # Create sample reviews
        self._create_reviews(options['reviews'])
        
        self.stdout.write(
            self.style.SUCCESS('✅ Database seeding completed successfully!')
        )

    def _create_users(self, count):
        """Create sample users"""
        self.stdout.write(f'👥 Creating {count} users...')
        
        for i in range(count):
            username = f'travel_user_{i+1}'
            email = fake.email()
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                }
            )
            
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(f'  ✓ Created user: {username}')
            else:
                self.stdout.write(f'  ⚠ User already exists: {username}')
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created/verified {count} users'))

    def _create_listings(self, count):
        """Create sample listings"""
        self.stdout.write(f'🏠 Creating {count} listings...')
        
        users = list(User.objects.all())
        property_types = ['apartment', 'house', 'villa', 'cottage', 'hotel']
        locations = [
            'Miami Beach, FL', 'Downtown LA, CA', 'Times Square, NY',
            'Fisherman\'s Wharf, CA', 'French Quarter, LA', 'Banff, AB',
            'Cancun Beach, Mexico', 'Lake Tahoe, CA', 'Key West, FL',
            'Asheville, NC', 'Santa Fe, NM', 'Portland, OR'
        ]
        
        created_count = 0
        for i in range(count):
            listing = Listing.objects.create(
                title=f"{fake.real_estate_type().title()} in {fake.city()}",
                description=fake.paragraph(nb_sentences=random.randint(2, 4)),
                property_type=random.choice(property_types),
                price_per_night=round(Decimal(random.uniform(45, 350)), 2),
                bedrooms=random.randint(1, 4),
                bathrooms=random.randint(1, 3),
                max_guests=random.randint(2, 8),
                location=random.choice(locations),
                owner=random.choice(users),
                is_available=random.choice([True, True, True, False])  # 75% available
            )
            
            created_count += 1
            if created_count % 5 == 0:
                self.stdout.write(f'  ✓ Created {created_count}/{count} listings')
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} listings'))

    def _create_bookings(self, count):
        """Create sample bookings"""
        self.stdout.write(f'📅 Creating {count} bookings...')
        
        available_listings = list(Listing.objects.filter(is_available=True))
        users = list(User.objects.all())
        
        if not available_listings:
            self.stdout.write(self.style.WARNING('No available listings found. Skipping bookings.'))
            return
        
        created_count = 0
        for i in range(count):
            listing = random.choice(available_listings)
            
            # Generate dates within the last year
            start_date = fake.date_between(start_date='-1y', end_date='-1m')
            nights = random.randint(2, 14)
            end_date = start_date + timedelta(days=nights)
            
            # Calculate total price
            total_price = listing.total_price_for_nights(nights)
            
            booking = Booking.objects.create(
                listing=listing,
                guest=random.choice(users),
                check_in_date=start_date,
                check_out_date=end_date,
                total_price=round(total_price, 2),
                status=random.choice(['pending', 'confirmed', 'completed'])
            )
            
            created_count += 1
            if created_count % 10 == 0:
                self.stdout.write(f'  ✓ Created {created_count}/{count} bookings')
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} bookings'))

    def _create_reviews(self, count):
        """Create sample reviews"""
        self.stdout.write(f'⭐ Creating {count} reviews...')
        
        listings = list(Listing.objects.all())
        users = list(User.objects.all())
        
        if not listings:
            self.stdout.write(self.style.WARNING('No listings found. Skipping reviews.'))
            return
        
        created_count = 0
        for i in range(count):
            listing = random.choice(listings)
            user = random.choice(users)
            
            # Skip if user already reviewed this listing
            if Review.objects.filter(listing=listing, user=user).exists():
                continue
            
            review = Review.objects.create(
                listing=listing,
                user=user,
                rating=random.randint(1, 5),
                comment=fake.paragraph(nb_sentences=random.randint(1, 3))
            )
            
            created_count += 1
            if created_count % 5 == 0:
                self.stdout.write(f'  ✓ Created {created_count}/{count} reviews')
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} reviews'))
