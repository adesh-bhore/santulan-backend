"""Daily Analysis Job for Ghost Bus Suppression

Analyzes historical passenger counts and creates suppression recommendations.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date, time
import logging
import os

from app.drt.passenger_count import PassengerCountService
from app.drt.ghost_bus import GhostBusService

logger = logging.getLogger(__name__)


def run_daily_analysis(db: Session):
    """
    Run daily analysis to identify low-demand trips and create suppression recommendations.
    
    This job should run daily at 2 AM to:
    1. Analyze historical passenger counts
    2. Identify consistently low-demand trips
    3. Create suppression recommendations for next 7 days
    4. Log results
    
    Args:
        db: Database session
    """
    try:
        logger.info("=" * 60)
        logger.info("Starting daily ghost bus analysis job")
        logger.info(f"Timestamp: {datetime.now()}")
        logger.info("=" * 60)
        
        # Get configuration
        threshold = int(os.getenv('DRT_SUPPRESSION_THRESHOLD', '5'))
        analysis_days = int(os.getenv('DRT_SUPPRESSION_ANALYSIS_DAYS', '30'))
        min_occurrences = int(os.getenv('DRT_SUPPRESSION_MIN_OCCURRENCES', '3'))
        
        logger.info(f"Configuration:")
        logger.info(f"  - Threshold: {threshold} passengers")
        logger.info(f"  - Analysis window: {analysis_days} days")
        logger.info(f"  - Min occurrences: {min_occurrences}")
        
        # Initialize services
        count_service = PassengerCountService(db)
        ghost_service = GhostBusService(db)
        
        # Step 1: Identify low-demand patterns
        logger.info("\nStep 1: Identifying low-demand trip patterns...")
        low_demand_patterns = count_service.get_low_demand_patterns(
            threshold=threshold,
            days=analysis_days
        )
        
        logger.info(f"Found {len(low_demand_patterns)} low-demand patterns")
        
        if not low_demand_patterns:
            logger.info("No low-demand patterns found. Analysis complete.")
            return {
                'status': 'success',
                'patterns_found': 0,
                'recommendations_created': 0
            }
        
        # Step 2: Create suppression recommendations for next 7 days
        logger.info("\nStep 2: Creating suppression recommendations...")
        recommendations_created = 0
        
        # Get date range for next 7 days
        today = date.today()
        date_range = [today + timedelta(days=i) for i in range(1, 8)]
        
        for pattern in low_demand_patterns:
            route_id = pattern['route_id']
            trip_time = pattern['trip_time']
            avg_count = pattern['avg_passenger_count']
            occurrences = pattern['occurrences']
            
            logger.info(f"\nProcessing pattern:")
            logger.info(f"  - Route: {route_id}")
            logger.info(f"  - Time: {trip_time}")
            logger.info(f"  - Avg passengers: {avg_count:.1f}")
            logger.info(f"  - Occurrences: {occurrences}")
            
            # Create recommendations for each day in next 7 days
            for scheduled_date in date_range:
                try:
                    # Generate trip ID (you may need to adjust this based on your trip ID format)
                    trip_id = f"TRIP_{route_id}_{scheduled_date.strftime('%Y%m%d')}_{trip_time.strftime('%H%M')}"
                    
                    # Create suppression recommendation
                    suppression = ghost_service.recommend_suppression(
                        trip_id=trip_id,
                        route_id=route_id,
                        scheduled_date=scheduled_date,
                        scheduled_time=trip_time,
                        reason=f"Low demand detected: Average {avg_count:.1f} passengers over {occurrences} trips in last {analysis_days} days",
                        avg_passenger_count=avg_count,
                        historical_days_analyzed=analysis_days
                    )
                    
                    recommendations_created += 1
                    logger.info(f"  ✓ Created suppression {suppression.suppression_id} for {scheduled_date}")
                    
                except Exception as e:
                    logger.warning(f"  ✗ Failed to create suppression for {scheduled_date}: {str(e)}")
                    continue
        
        # Step 3: Summary
        logger.info("\n" + "=" * 60)
        logger.info("Daily analysis job completed")
        logger.info(f"  - Patterns found: {len(low_demand_patterns)}")
        logger.info(f"  - Recommendations created: {recommendations_created}")
        logger.info("=" * 60)
        
        return {
            'status': 'success',
            'patterns_found': len(low_demand_patterns),
            'recommendations_created': recommendations_created
        }
        
    except Exception as e:
        logger.error(f"Daily analysis job failed: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'error': str(e)
        }


def run_daily_analysis_wrapper():
    """Wrapper function for APScheduler"""
    from app.database.db import SessionLocal
    
    db = SessionLocal()
    try:
        return run_daily_analysis(db)
    finally:
        db.close()


# Alias for compatibility
run_daily_ghost_bus_analysis = run_daily_analysis
