# Weather Integration Module - Product Requirements Document

## Module Overview
**Module Name:** Weather Integration Module (Module 3/4)  
**Timeline:** Iteration 2 (Months 3-4)  
**Owner:** Hafsa Waqar (22I-2625)  
**Dependencies:** Backend API, Redis Cache, Database Setup

## Objectives
1. Integrate real-time weather data for orchard locations
2. Provide automated weather-based alerts to users
3. Analyze weather-disease correlations for risk assessment
4. Support decision-making for irrigation and disease prevention

---

## API Integration

### Primary API: OpenWeatherMap API
**Base URL:** `https://api.openweathermap.org/data/2.5`

#### Required Endpoints:
1. **Current Weather API**
   - Endpoint: `/weather`
   - Purpose: Get current weather conditions for orchard location
   - Key Data: Temperature, humidity, pressure, wind speed, precipitation

2. **5-Day Forecast API**
   - Endpoint: `/forecast`
   - Purpose: Get weather predictions for next 5 days
   - Key Data: 3-hour interval forecasts, temperature trends, rainfall predictions

3. **Weather Alerts API** (Optional Premium)
   - Endpoint: `/onecall`
   - Purpose: Get severe weather warnings
   - Key Data: Storm alerts, extreme temperature warnings

#### API Requirements:
- Require API Key (free tier: 1000 calls/day)
- Use metric units (Celsius, km/h)
- Support GPS coordinates (latitude, longitude)
- Response format: JSON

---

## Database Tables

### 1. `orchards`
**Purpose:** Store orchard location and user mapping  
**Key Fields:**
- `id` (Primary Key)
- `user_id` (Foreign Key → users table)
- `name` (varchar)
- `latitude` (decimal)
- `longitude` (decimal)
- `area_hectares` (decimal)
- `fruit_types` (JSON array: ["mango", "guava"])
- `created_at`, `updated_at`

### 2. `weather_data`
**Purpose:** Store historical weather records for analysis  
**Key Fields:**
- `id` (Primary Key)
- `orchard_id` (Foreign Key → orchards)
- `temperature` (decimal)
- `humidity` (decimal)
- `rainfall` (decimal)
- `wind_speed` (decimal)
- `weather_condition` (varchar: "clear", "rain", "cloudy")
- `recorded_at` (timestamp)
- `source` (varchar: "openweathermap")

### 3. `weather_alerts`
**Purpose:** Store alert rules and triggered alerts  
**Key Fields:**
- `id` (Primary Key)
- `orchard_id` (Foreign Key → orchards)
- `alert_type` (varchar: "high_humidity", "rainfall", "extreme_temp")
- `severity` (enum: "low", "medium", "high")
- `message` (text)
- `recommendation` (text)
- `is_active` (boolean)
- `triggered_at` (timestamp)
- `acknowledged_at` (timestamp, nullable)

### 4. `alert_rules`
**Purpose:** Configurable thresholds for weather alerts  
**Key Fields:**
- `id` (Primary Key)
- `rule_name` (varchar)
- `condition_type` (varchar: "humidity", "temperature", "rainfall")
- `threshold_value` (decimal)
- `operator` (varchar: ">", "<", ">=", "<=")
- `disease_risk` (varchar: "anthracnose", "citrus_canker")
- `fruit_types` (JSON array)
- `alert_message_en` (text)
- `alert_message_ur` (text)
- `is_enabled` (boolean)

### 5. `weather_disease_risk`
**Purpose:** Store calculated risk assessments  
**Key Fields:**
- `id` (Primary Key)
- `orchard_id` (Foreign Key → orchards)
- `disease_type` (varchar)
- `risk_level` (enum: "low", "medium", "high")
- `contributing_factors` (JSON)
- `recommendation_en` (text)
- `recommendation_ur` (text)
- `calculated_at` (timestamp)

---

## Backend Implementation Requirements

### 1. Weather Data Service
**Responsibilities:**
- Fetch current weather from OpenWeatherMap API
- Fetch 5-day forecast data
- Cache responses in Redis (TTL: 30 minutes)
- Handle API rate limiting and errors
- Convert coordinates to location names (reverse geocoding)

**Key Functions:**
- `get_current_weather(orchard_id)`
- `get_forecast(orchard_id, days=5)`
- `update_weather_cache()`
- `get_weather_history(orchard_id, date_range)`

### 2. Alert System Service
**Responsibilities:**
- Evaluate weather conditions against alert rules
- Generate alerts when thresholds are exceeded
- Send notifications via FCM (mobile) and WebSocket (web)
- Track alert acknowledgment status
- Support bilingual alert messages

**Key Functions:**
- `evaluate_alert_rules(orchard_id)`
- `create_alert(orchard_id, alert_type, severity)`
- `send_notification(user_id, alert_data)`
- `acknowledge_alert(alert_id)`

### 3. Risk Analysis Service
**Responsibilities:**
- Correlate weather patterns with disease likelihood
- Calculate risk scores based on multiple weather factors
- Provide actionable recommendations
- Track historical accuracy of predictions

**Key Functions:**
- `calculate_disease_risk(orchard_id, fruit_type)`
- `get_risk_factors(weather_data, disease_type)`
- `generate_recommendations(risk_data)`

**Risk Calculation Rules:**
| Disease | Weather Conditions | Risk Level |
|---------|-------------------|------------|
| Anthracnose | Humidity > 75%, Temp 25-35°C, Recent rain | High |
| Citrus Canker | High humidity, Temp > 30°C, Windy | High |
| Black Spot | Humid, Temp 24-29°C, Wet leaves | Medium-High |
| Fruit Fly | Dry spell, Temp > 25°C | Medium |

### 4. Background Tasks (Celery)
**Scheduled Tasks:**
- Fetch weather data every 30 minutes for all active orchards
- Evaluate alert rules every 30 minutes
- Store weather snapshots to database every 2 hours
- Clean up old weather data (keep 90 days)

### 5. API Endpoints

**Weather Endpoints:**
- `GET /api/weather/current/{orchard_id}` - Get current weather
- `GET /api/weather/forecast/{orchard_id}` - Get 5-day forecast
- `GET /api/weather/history/{orchard_id}` - Get historical data

**Alert Endpoints:**
- `GET /api/alerts/active/{orchard_id}` - Get active alerts
- `POST /api/alerts/acknowledge/{alert_id}` - Mark alert as read
- `GET /api/alerts/rules` - Get alert rule configurations
- `PUT /api/alerts/rules/{rule_id}` - Update alert thresholds (admin)

**Risk Assessment Endpoints:**
- `GET /api/risk/current/{orchard_id}` - Get current risk assessment
- `GET /api/risk/forecast/{orchard_id}` - Get predicted risks

---

## Frontend Implementation Requirements

### Mobile App (React Native)

#### 1. Weather Dashboard Screen
**Components:**
- Current weather card (temp, humidity, condition icon)
- 5-day forecast horizontal scroll
- Risk indicator badges (color-coded: red/yellow/green)
- Weather-based recommendations section

**Features:**
- Pull-to-refresh for latest data
- Location-based weather (select orchard)
- Switch between English/Urdu
- Tap weather card for detailed view

#### 2. Weather Alerts Screen
**Components:**
- Alert list (grouped by severity)
- Alert detail modal
- Notification badge on tab icon
- Filter by alert type

**Features:**
- Real-time push notifications
- Swipe to acknowledge alert
- View historical alerts (last 7 days)
- Alert sound/vibration toggle in settings

#### 3. Weather Detail Screen
**Components:**
- Detailed weather metrics (pressure, wind, UV index)
- Hourly forecast chart
- Sunrise/sunset times
- "Feels like" temperature

#### 4. Notifications
**Types:**
- High humidity alert (anthracnose risk)
- Rainfall warning
- Extreme temperature alert
- Irrigation recommendation

**Notification Format:**
```
Title: "High Humidity Alert - Mango Orchard"
Body: "Humidity 82%, Temp 28°C. High anthracnose risk. Consider preventive spray."
Action: "View Details"
```

### Web Dashboard (React/Next.js)

#### 1. Weather Widget (Dashboard)
**Components:**
- Compact weather summary card
- Quick risk indicators
- Mini forecast (3-day)
- Last updated timestamp

**Placement:**
- Top-right of main dashboard
- Always visible
- Click to expand full weather page

#### 2. Weather & Risk Analysis Page
**Components:**
- Large weather overview section
- Disease risk assessment cards (one per disease)
- Weather history chart (7-day trend)
- Forecast table (5-day detailed)
- Alert management panel

**Charts:**
- Temperature & humidity line chart
- Rainfall bar chart
- Risk score gauge chart

#### 3. Alert Management Panel
**Components:**
- Active alerts table
- Alert history log
- Configure alert preferences
- Test notification button

**Features:**
- Bulk acknowledge alerts
- Export alert history (CSV)
- Set custom thresholds (admin users)

#### 4. Weather-Disease Correlation View
**Components:**
- Side-by-side comparison: weather conditions vs disease outbreaks
- Historical correlation heatmap
- Prediction accuracy metrics

---

## Caching Strategy (Redis)

### Cache Keys Structure:
- `weather:current:{orchard_id}` → TTL: 30 minutes
- `weather:forecast:{orchard_id}` → TTL: 2 hours
- `weather:alerts:{orchard_id}` → TTL: 5 minutes
- `risk:assessment:{orchard_id}` → TTL: 1 hour

### Cache Invalidation:
- Manual refresh by user
- Scheduled update every 30 minutes
- Alert rule change

---

## Notification System

### Push Notifications (Mobile - FCM)
**Triggers:**
- High-priority weather alert
- Severe weather warning
- Disease risk threshold exceeded

**Configuration:**
- User can enable/disable per alert type
- Quiet hours setting (no alerts 10 PM - 6 AM)
- Alert frequency limit (max 3 per day per type)

### Real-time Updates (Web - WebSocket)
**Triggers:**
- Weather data refresh
- New alert triggered
- Risk level change

**Implementation:**
- WebSocket connection on dashboard load
- Automatic reconnection on disconnect
- Show toast notification for new alerts

---

## Bilingual Support Requirements

### Language Support: English & Urdu

**Translated Content:**
- Weather condition descriptions
- Alert messages
- Risk recommendations
- UI labels and buttons

**Translation Keys Required:**
- Weather conditions: "Clear", "Rain", "Cloudy", "Storm"
- Alert types: "High Humidity", "Rainfall", "Extreme Temperature"
- Risk levels: "Low", "Medium", "High"
- Recommendations: Full sentences in both languages

**Storage:**
- Store both `message_en` and `message_ur` in database
- Frontend uses i18n library for UI translations
- API returns both language versions, frontend selects based on user preference

---

## Success Metrics

### Technical Metrics:
- Weather data fetch success rate > 99%
- API response time < 500ms (with caching)
- Alert delivery time < 30 seconds
- Cache hit rate > 80%

### User Metrics:
- Alert acknowledgment rate
- Weather dashboard view frequency
- Risk recommendation follow-through
- User-reported accuracy of predictions

---

## Testing Requirements

### Unit Tests:
- Weather API integration
- Alert rule evaluation logic
- Risk calculation algorithms
- Cache operations

### Integration Tests:
- End-to-end alert flow
- Weather data → risk assessment → notification
- Multi-orchard handling

### Manual Testing:
- Mock different weather scenarios
- Test bilingual content
- Verify push notifications on mobile
- Test with actual GPS coordinates of orchards in Pakistan

---

## Security & Privacy

**API Key Management:**
- Store OpenWeatherMap API key in environment variables
- Never expose in frontend code
- Rotate keys if compromised

**Data Privacy:**
- Orchard location data is user-private
- Weather data is not shared between users
- Alerts are user-specific

**Rate Limiting:**
- Implement backend rate limiting (prevent API abuse)
- User cannot trigger more than 10 manual refreshes per hour

---

## Future Enhancements (Out of Scope for Current Iteration)

- Historical weather pattern ML model for better predictions
- Integration with soil moisture sensors
- Farmer-reported weather conditions (crowdsourcing)
- Weather-based irrigation scheduling automation
- Integration with Pakistan Meteorological Department API

---

## Deliverables (Iteration 2 - Months 3-4)

### Week 1-2:
- [ ] OpenWeatherMap API integration complete
- [ ] Redis caching implementation
- [ ] Database tables created and migrated
- [ ] Basic weather endpoints functional

### Week 3-4:
- [ ] Alert system logic implemented
- [ ] Celery background tasks running
- [ ] FCM push notifications working
- [ ] Mobile weather dashboard complete

### Week 5-6:
- [ ] Risk analysis algorithms implemented
- [ ] Weather-disease correlation rules active
- [ ] Web dashboard weather widgets complete
- [ ] Bilingual support fully functional

### Week 7-8:
- [ ] Integration testing complete
- [ ] User acceptance testing
- [ ] Performance optimization
- [ ] Documentation complete

---

## Dependencies & Prerequisites

**Before Starting:**
- OpenWeatherMap API account created
- Redis server set up
- FCM project configured for mobile app
- Database migrations ready
- User authentication system functional

**External Dependencies:**
- OpenWeatherMap API availability
- Internet connectivity for API calls
- FCM service operational

**Team Dependencies:**
- Module 1 (Object Detection) - provides fruit type data
- Module 2 (Disease Detection) - provides disease types for correlation
- Module 9 (Client Apps) - frontend implementation collaboration

---

## Risk Mitigation

| Risk | Impact | Mitigation Strategy |
|------|--------|-------------------|
| API rate limits exceeded | High | Aggressive caching, upgrade to paid tier if needed |
| API downtime | Medium | Implement fallback to cached data, show last known values |
| Inaccurate risk predictions | Medium | Continuous validation against actual disease outbreaks, refine rules |
| Poor notification adoption | Low | Make alerts actionable, allow customization, avoid notification fatigue |

---

**Document Version:** 1.0  
**Last Updated:** December 2025  
**Next Review:** After Iteration 2 completion