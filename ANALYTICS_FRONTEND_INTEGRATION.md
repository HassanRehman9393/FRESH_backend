# Analytics Frontend Integration Guide

This guide provides comprehensive information for integrating the FRESH Analytics API endpoints with your frontend application.

## Base URL

```
Production: https://your-backend-url.com
Development: http://localhost:8080
```

## Authentication

All analytics endpoints require JWT authentication. Include the access token in the Authorization header:

```javascript
headers: {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
}
```

## Available Endpoints

### 1. Quality Analytics

**Endpoint:** `GET /api/analytics/quality`

**Description:** Get comprehensive fruit quality analytics including fruit type statistics, ripeness distribution, quality scores, and defect analysis.

**Query Parameters:**
- `start_date` (optional): Start date for analysis (YYYY-MM-DD)
- `end_date` (optional): End date for analysis (YYYY-MM-DD)
- Default: Last 30 days if dates not specified

**Request Example:**
```javascript
const getQualityAnalytics = async (startDate, endDate) => {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  
  const response = await fetch(
    `${API_BASE_URL}/api/analytics/quality?${params.toString()}`,
    {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      }
    }
  );
  
  return await response.json();
};
```

**Response Schema:**
```typescript
interface QualityAnalyticsResponse {
  user_id: string;
  date_range: {
    start: string;  // ISO date
    end: string;    // ISO date
  };
  total_detections: number;
  total_images: number;
  fruit_statistics: Array<{
    fruit_type: string;
    total_count: number;
    average_confidence: number;
    ripeness_distribution: {
      ripe?: number;
      unripe?: number;
      overripe?: number;
      unknown?: number;
    };
    quality_score_avg: number | null;
    defect_rate: number;
    common_defects: string[] | null;
  }>;
  overall_quality_score: number;
  best_performing_fruit: string | null;
  worst_performing_fruit: string | null;
  generated_at: string;  // ISO timestamp
}
```

**Sample Response:**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "date_range": {
    "start": "2025-11-01",
    "end": "2025-12-01"
  },
  "total_detections": 150,
  "total_images": 45,
  "fruit_statistics": [
    {
      "fruit_type": "apple",
      "total_count": 60,
      "average_confidence": 0.95,
      "ripeness_distribution": {
        "ripe": 45,
        "unripe": 10,
        "overripe": 5
      },
      "quality_score_avg": 92.5,
      "defect_rate": 8.3,
      "common_defects": ["bruising", "spots"]
    }
  ],
  "overall_quality_score": 88.7,
  "best_performing_fruit": "apple",
  "worst_performing_fruit": "banana",
  "generated_at": "2025-12-01T10:30:00Z"
}
```

---

### 2. Quality Trends

**Endpoint:** `GET /api/analytics/quality/trends`

**Description:** Get fruit quality trends over time showing daily quality score progression, defect rate trends, and detection volume trends.

**Query Parameters:**
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)

**Request Example:**
```javascript
const getQualityTrends = async (startDate, endDate) => {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  
  const response = await fetch(
    `${API_BASE_URL}/api/analytics/quality/trends?${params.toString()}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};
```

**Response Schema:**
```typescript
interface QualityTrendResponse {
  user_id: string;
  date_range: {
    start: string;
    end: string;
  };
  trends: Array<{
    date: string;
    total_detections: number;
    average_quality_score: number;
    defect_rate: number;
  }>;
  generated_at: string;
}
```

---

### 3. Disease Risk Analytics

**Endpoint:** `GET /api/analytics/disease-risk`

**Description:** Get comprehensive disease risk analytics including disease statistics, infection rates, risk assessment, and actionable recommendations.

**Query Parameters:**
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)

**Request Example:**
```javascript
const getDiseaseRiskAnalytics = async (startDate, endDate) => {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  
  const response = await fetch(
    `${API_BASE_URL}/api/analytics/disease-risk?${params.toString()}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};
```

**Response Schema:**
```typescript
interface DiseaseRiskAnalyticsResponse {
  user_id: string;
  date_range: {
    start: string;
    end: string;
  };
  total_detections: number;
  diseased_count: number;
  healthy_count: number;
  infection_rate: number;
  disease_statistics: Array<{
    disease_type: string;
    count: number;
    average_confidence: number;
    severity_distribution: {
      low?: number;
      medium?: number;
      high?: number;
      critical?: number;
    };
    affected_fruits: string[];
  }>;
  overall_risk_level: "low" | "medium" | "high" | "critical";
  recommendations: string[];
  generated_at: string;
}
```

**Sample Response:**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "date_range": {
    "start": "2025-11-01",
    "end": "2025-12-01"
  },
  "total_detections": 150,
  "diseased_count": 15,
  "healthy_count": 135,
  "infection_rate": 10.0,
  "disease_statistics": [
    {
      "disease_type": "anthracnose",
      "count": 10,
      "average_confidence": 0.87,
      "severity_distribution": {
        "low": 5,
        "medium": 3,
        "high": 2
      },
      "affected_fruits": ["mango", "guava"]
    }
  ],
  "overall_risk_level": "medium",
  "recommendations": [
    "⚡ MODERATE RISK: Maintain regular monitoring and preventive measures",
    "For Anthracnose: Apply appropriate fungicides and improve air circulation"
  ],
  "generated_at": "2025-12-01T10:30:00Z"
}
```

---

### 4. Disease Risk Trends

**Endpoint:** `GET /api/analytics/disease-risk/trends`

**Description:** Track disease risk changes over time with daily infection rates and disease detection patterns.

**Query Parameters:**
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)

**Request Example:**
```javascript
const getDiseaseRiskTrends = async (startDate, endDate) => {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  
  const response = await fetch(
    `${API_BASE_URL}/api/analytics/disease-risk/trends?${params.toString()}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};
```

---

### 5. Yield Analytics

**Endpoint:** `GET /api/analytics/yield`

**Description:** Get yield analytics including total fruit count by type, marketable fruit count and percentage, estimated weight calculations, and best performing fruit types.

**Marketable Criteria:**
- Ripeness: ripe or unripe (not overripe/rotten)
- Defects: maximum 1 minor defect
- Quality score: minimum 60/100

**Query Parameters:**
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)

**Request Example:**
```javascript
const getYieldAnalytics = async (startDate, endDate) => {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  
  const response = await fetch(
    `${API_BASE_URL}/api/analytics/yield?${params.toString()}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};
```

**Response Schema:**
```typescript
interface YieldAnalyticsResponse {
  user_id: string;
  date_range: {
    start: string;
    end: string;
  };
  total_fruit_count: number;
  total_marketable_count: number;
  overall_marketable_rate: number;
  fruit_yields: Array<{
    fruit_type: string;
    total_count: number;
    marketable_count: number;
    marketable_percentage: number;
    estimated_weight_kg: number | null;
  }>;
  estimated_total_weight_kg: number | null;
  best_yielding_fruit: string | null;
  generated_at: string;
}
```

**Sample Response:**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "date_range": {
    "start": "2025-11-01",
    "end": "2025-12-01"
  },
  "total_fruit_count": 150,
  "total_marketable_count": 120,
  "overall_marketable_rate": 80.0,
  "fruit_yields": [
    {
      "fruit_type": "apple",
      "total_count": 60,
      "marketable_count": 52,
      "marketable_percentage": 86.7,
      "estimated_weight_kg": 12.0
    }
  ],
  "estimated_total_weight_kg": 35.5,
  "best_yielding_fruit": "apple",
  "generated_at": "2025-12-01T10:30:00Z"
}
```

---

### 6. Yield Comparison

**Endpoint:** `GET /api/analytics/yield/comparison`

**Description:** Compare yield between current period and previous period with growth rate calculation.

**Query Parameters:**
- `start_date` (optional): Start date for current period (YYYY-MM-DD)
- `end_date` (optional): End date for current period (YYYY-MM-DD)

**Request Example:**
```javascript
const getYieldComparison = async (startDate, endDate) => {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  
  const response = await fetch(
    `${API_BASE_URL}/api/analytics/yield/comparison?${params.toString()}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};
```

**Response Schema:**
```typescript
interface YieldComparisonResponse {
  current_period: YieldAnalyticsResponse;
  previous_period: YieldAnalyticsResponse | null;
  growth_rate: number | null;  // Percentage change
  generated_at: string;
}
```

---

### 7. Export Readiness

**Endpoint:** `GET /api/analytics/export-readiness`

**Description:** Get comprehensive export readiness report including export quality compliance metrics, ripeness/size/defect compliance, disease-free rate, overall readiness score, rejection reasons analysis, and market-specific recommendations.

**Export Readiness Criteria:**
- Overall compliance score ≥ 75%
- Disease-free
- Appropriate ripeness level
- Size standards met
- Minimal defects

**Readiness Score Interpretation:**
- 90-100%: Premium export markets (EU, US, Japan)
- 75-89%: Standard export markets (Asia, Middle East)
- 60-74%: Domestic markets recommended
- <60%: Processing/juice markets

**Query Parameters:**
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)
- `target_market` (optional): Target export market (e.g., 'EU', 'US', 'Asia')

**Request Example:**
```javascript
const getExportReadiness = async (startDate, endDate, targetMarket) => {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  if (targetMarket) params.append('target_market', targetMarket);
  
  const response = await fetch(
    `${API_BASE_URL}/api/analytics/export-readiness?${params.toString()}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};
```

**Response Schema:**
```typescript
interface ExportReadinessResponse {
  user_id: string;
  report_date: string;
  date_range: {
    start: string;
    end: string;
  };
  total_fruit_analyzed: number;
  total_export_ready: number;
  overall_readiness_score: number;
  fruit_readiness: Array<{
    fruit_type: string;
    total_count: number;
    export_ready_count: number;
    export_ready_percentage: number;
    quality_metrics: {
      ripeness_compliance: number;
      size_compliance: number;
      defect_compliance: number;
      disease_free_rate: number;
      overall_compliance: number;
    };
    rejection_reasons: Record<string, number>;
    recommended_actions: string[];
  }>;
  market_recommendations: string[];
  compliance_summary: {
    export_ready_rate: number;
    average_compliance_score: number;
    total_analyzed: number;
    total_export_ready: number;
    rejection_rate: number;
    target_market: string;
  };
  generated_at: string;
}
```

**Sample Response:**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "report_date": "2025-12-01T10:30:00Z",
  "date_range": {
    "start": "2025-11-01",
    "end": "2025-12-01"
  },
  "total_fruit_analyzed": 150,
  "total_export_ready": 120,
  "overall_readiness_score": 80.0,
  "fruit_readiness": [
    {
      "fruit_type": "apple",
      "total_count": 60,
      "export_ready_count": 52,
      "export_ready_percentage": 86.7,
      "quality_metrics": {
        "ripeness_compliance": 90.0,
        "size_compliance": 95.0,
        "defect_compliance": 85.0,
        "disease_free_rate": 98.0,
        "overall_compliance": 92.0
      },
      "rejection_reasons": {
        "Poor ripeness": 3,
        "Surface defects": 5
      },
      "recommended_actions": [
        "Maintain current quality standards"
      ]
    }
  ],
  "market_recommendations": [
    "✅ Standard export markets (Asia, Middle East) - Good quality",
    "Consider quality improvements for premium markets"
  ],
  "compliance_summary": {
    "export_ready_rate": 80.0,
    "average_compliance_score": 85.5,
    "total_analyzed": 150,
    "total_export_ready": 120,
    "rejection_rate": 20.0,
    "target_market": "EU"
  },
  "generated_at": "2025-12-01T10:30:00Z"
}
```

---

### 8. Analytics Summary

**Endpoint:** `GET /api/analytics/summary`

**Description:** Get comprehensive analytics summary combining all metrics including quality, disease risk, yield, and export readiness.

**Query Parameters:**
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)

**Request Example:**
```javascript
const getAnalyticsSummary = async (startDate, endDate) => {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  
  const response = await fetch(
    `${API_BASE_URL}/api/analytics/summary?${params.toString()}`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    }
  );
  
  return await response.json();
};
```

**Response Schema:**
```typescript
interface AnalyticsSummaryResponse {
  user_id: string;
  date_range: {
    start: string;
    end: string;
  };
  quality_score: number;
  disease_risk_level: "low" | "medium" | "high" | "critical";
  marketable_rate: number;
  export_readiness_score: number;
  total_fruit_analyzed: number;
  key_insights: string[];
  areas_for_improvement: string[];
  generated_at: string;
}
```

**Sample Response:**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "date_range": {
    "start": "2025-11-01",
    "end": "2025-12-01"
  },
  "quality_score": 88.7,
  "disease_risk_level": "low",
  "marketable_rate": 80.0,
  "export_readiness_score": 85.5,
  "total_fruit_analyzed": 150,
  "key_insights": [
    "Quality performance is excellent",
    "Disease management is effective",
    "Export standards are being met"
  ],
  "areas_for_improvement": [
    "✅ All metrics performing well - maintain current practices"
  ],
  "generated_at": "2025-12-01T10:30:00Z"
}
```

---

## Error Handling

All endpoints follow a consistent error response format:

```typescript
interface ErrorResponse {
  detail: string;
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `401`: Unauthorized (missing or invalid token)
- `404`: Not Found
- `500`: Internal Server Error

**Error Handling Example:**
```javascript
const handleAnalyticsRequest = async () => {
  try {
    const data = await getQualityAnalytics('2025-11-01', '2025-12-01');
    return data;
  } catch (error) {
    if (error.status === 401) {
      // Handle authentication error - redirect to login
      console.error('Authentication failed');
    } else if (error.status === 500) {
      // Handle server error
      console.error('Server error:', error.detail);
    } else {
      // Handle other errors
      console.error('Request failed:', error);
    }
  }
};
```

---

## React Integration Example

### Custom Hook for Analytics

```javascript
// hooks/useAnalytics.js
import { useState, useEffect } from 'react';
import { useAuth } from './useAuth'; // Your auth hook

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

export const useAnalytics = () => {
  const { accessToken } = useAuth();
  
  const fetchAnalytics = async (endpoint, params = {}) => {
    const queryString = new URLSearchParams(params).toString();
    const url = `${API_BASE_URL}${endpoint}${queryString ? '?' + queryString : ''}`;
    
    const response = await fetch(url, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Request failed');
    }
    
    return await response.json();
  };
  
  return {
    getQualityAnalytics: (startDate, endDate) => 
      fetchAnalytics('/api/analytics/quality', { start_date: startDate, end_date: endDate }),
    
    getDiseaseRisk: (startDate, endDate) => 
      fetchAnalytics('/api/analytics/disease-risk', { start_date: startDate, end_date: endDate }),
    
    getYieldAnalytics: (startDate, endDate) => 
      fetchAnalytics('/api/analytics/yield', { start_date: startDate, end_date: endDate }),
    
    getExportReadiness: (startDate, endDate, targetMarket) => 
      fetchAnalytics('/api/analytics/export-readiness', { 
        start_date: startDate, 
        end_date: endDate,
        target_market: targetMarket 
      }),
    
    getAnalyticsSummary: (startDate, endDate) => 
      fetchAnalytics('/api/analytics/summary', { start_date: startDate, end_date: endDate })
  };
};
```

### Component Example

```javascript
// components/QualityDashboard.jsx
import React, { useState, useEffect } from 'react';
import { useAnalytics } from '../hooks/useAnalytics';

const QualityDashboard = () => {
  const [qualityData, setQualityData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dateRange, setDateRange] = useState({
    start: '2025-11-01',
    end: '2025-12-01'
  });
  
  const analytics = useAnalytics();
  
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const data = await analytics.getQualityAnalytics(
          dateRange.start, 
          dateRange.end
        );
        setQualityData(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    
    loadData();
  }, [dateRange]);
  
  if (loading) return <div>Loading analytics...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!qualityData) return <div>No data available</div>;
  
  return (
    <div className="quality-dashboard">
      <h2>Quality Analytics</h2>
      
      <div className="date-selector">
        <input 
          type="date" 
          value={dateRange.start}
          onChange={(e) => setDateRange({...dateRange, start: e.target.value})}
        />
        <input 
          type="date" 
          value={dateRange.end}
          onChange={(e) => setDateRange({...dateRange, end: e.target.value})}
        />
      </div>
      
      <div className="summary-cards">
        <div className="card">
          <h3>Overall Quality Score</h3>
          <p className="score">{qualityData.overall_quality_score}</p>
        </div>
        
        <div className="card">
          <h3>Total Detections</h3>
          <p>{qualityData.total_detections}</p>
        </div>
        
        <div className="card">
          <h3>Best Performing</h3>
          <p>{qualityData.best_performing_fruit || 'N/A'}</p>
        </div>
      </div>
      
      <div className="fruit-statistics">
        <h3>Fruit Statistics</h3>
        {qualityData.fruit_statistics.map((fruit) => (
          <div key={fruit.fruit_type} className="fruit-card">
            <h4>{fruit.fruit_type}</h4>
            <p>Count: {fruit.total_count}</p>
            <p>Quality Score: {fruit.quality_score_avg}</p>
            <p>Defect Rate: {fruit.defect_rate}%</p>
            
            <div className="ripeness">
              <h5>Ripeness Distribution</h5>
              {Object.entries(fruit.ripeness_distribution).map(([key, value]) => (
                <span key={key}>{key}: {value} | </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default QualityDashboard;
```

---

## Vue.js Integration Example

### Composable for Analytics

```javascript
// composables/useAnalytics.js
import { ref } from 'vue';
import { useAuth } from './useAuth';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

export const useAnalytics = () => {
  const { accessToken } = useAuth();
  const loading = ref(false);
  const error = ref(null);
  
  const fetchAnalytics = async (endpoint, params = {}) => {
    loading.value = true;
    error.value = null;
    
    try {
      const queryString = new URLSearchParams(params).toString();
      const url = `${API_BASE_URL}${endpoint}${queryString ? '?' + queryString : ''}`;
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${accessToken.value}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Request failed');
      }
      
      return await response.json();
    } catch (err) {
      error.value = err.message;
      throw err;
    } finally {
      loading.value = false;
    }
  };
  
  return {
    loading,
    error,
    getQualityAnalytics: (startDate, endDate) => 
      fetchAnalytics('/api/analytics/quality', { start_date: startDate, end_date: endDate }),
    getDiseaseRisk: (startDate, endDate) => 
      fetchAnalytics('/api/analytics/disease-risk', { start_date: startDate, end_date: endDate }),
    getYieldAnalytics: (startDate, endDate) => 
      fetchAnalytics('/api/analytics/yield', { start_date: startDate, end_date: endDate }),
    getExportReadiness: (startDate, endDate, targetMarket) => 
      fetchAnalytics('/api/analytics/export-readiness', { 
        start_date: startDate, 
        end_date: endDate,
        target_market: targetMarket 
      }),
    getAnalyticsSummary: (startDate, endDate) => 
      fetchAnalytics('/api/analytics/summary', { start_date: startDate, end_date: endDate })
  };
};
```

---

## Data Visualization Recommendations

### Chart Libraries

1. **Chart.js** - Good for basic charts
2. **Recharts** - React-specific, easy to use
3. **D3.js** - Advanced, highly customizable
4. **Victory** - React Native compatible
5. **Apache ECharts** - Feature-rich, production-ready

### Recommended Visualizations

1. **Quality Analytics:**
   - Pie chart for ripeness distribution
   - Bar chart for fruit type comparison
   - Line chart for quality trends over time
   - Gauge/radial chart for overall quality score

2. **Disease Risk:**
   - Risk level indicator (colored badge/card)
   - Bar chart for disease type distribution
   - Heat map for severity distribution
   - Time series for infection rate trends

3. **Yield Analytics:**
   - Bar chart comparing total vs marketable count
   - Stacked bar for fruit type yields
   - Line chart for yield comparison between periods
   - Progress bar for marketable rate

4. **Export Readiness:**
   - Radar/spider chart for compliance metrics
   - Funnel chart for export readiness pipeline
   - Horizontal bar for rejection reasons
   - Score card with color coding (red/yellow/green)

---

## Best Practices

### 1. Caching Strategy
```javascript
// Cache analytics data to reduce API calls
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

class AnalyticsCache {
  constructor() {
    this.cache = new Map();
  }
  
  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;
    
    if (Date.now() - item.timestamp > CACHE_DURATION) {
      this.cache.delete(key);
      return null;
    }
    
    return item.data;
  }
  
  set(key, data) {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });
  }
}

const analyticsCache = new AnalyticsCache();
```

### 2. Loading States
Always show loading indicators while fetching analytics data.

### 3. Empty States
Handle cases where no data is available with helpful messages.

### 4. Error Boundaries
Wrap analytics components in error boundaries to prevent crashes.

### 5. Date Range Selection
- Provide preset options (Last 7 days, Last 30 days, Last 90 days)
- Allow custom date range selection
- Validate date ranges (end date should be after start date)

### 6. Progressive Enhancement
Load summary first, then detailed analytics on demand.

### 7. Export Functionality
Allow users to export analytics data as CSV/PDF for reporting.

---

## Testing Endpoints

### Using Swagger UI (Recommended for Development)

1. Navigate to `http://localhost:8080/docs`
2. Click "Authorize" button
3. Login to get your JWT token
4. Test any analytics endpoint interactively

### Using Postman

1. Create a collection for Analytics API
2. Set environment variable for `base_url` and `access_token`
3. Create requests for each endpoint
4. Use pre-request scripts to refresh token if needed

### Using cURL

```bash
# Login first
TOKEN=$(curl -X POST "http://localhost:8080/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' \
  | jq -r '.access_token')

# Get quality analytics
curl -X GET "http://localhost:8080/api/analytics/quality?start_date=2025-11-01&end_date=2025-12-01" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Support and Documentation

- **API Documentation:** http://localhost:8080/docs
- **Alternative Docs:** http://localhost:8080/redoc
- **Health Check:** http://localhost:8080/health

For issues or questions, please refer to the main `README.md` or `DEPLOYMENT.md` files.
