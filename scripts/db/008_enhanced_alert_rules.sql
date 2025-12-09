-- ============================================================================
-- Enhanced Alert Rules for Pakistani Fruits
-- Research-based thresholds for Mango, Guava, Citrus, Orange, Grapefruit
-- Climate: Pakistan (Hot subtropical to arid, monsoon patterns)
-- ============================================================================

-- Drop existing alert_rules table if exists
DROP TABLE IF EXISTS public.alert_rules CASCADE;

-- Create enhanced alert_rules table with fruit-specific conditions
CREATE TABLE IF NOT EXISTS public.alert_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Rule Identification
  rule_name VARCHAR(200) NOT NULL UNIQUE,
  rule_code VARCHAR(50) NOT NULL UNIQUE,  -- e.g., 'MANGO_HEAT_STRESS'
  description TEXT,
  
  -- Fruit Specificity
  fruit_types TEXT[] NOT NULL,  -- ['mango'], ['citrus', 'orange'], or ['all']
  growth_stages TEXT[],  -- ['flowering', 'fruiting', 'harvest'] or ['all']
  
  -- Weather Conditions (NULL means not checked)
  temperature_min DECIMAL(5, 2),
  temperature_max DECIMAL(5, 2),
  humidity_min DECIMAL(5, 2),
  humidity_max DECIMAL(5, 2),
  rainfall_min DECIMAL(6, 2),  -- mm
  rainfall_max DECIMAL(6, 2),
  wind_speed_max DECIMAL(5, 2),  -- km/h
  
  -- Forecast-based triggers
  consecutive_days INTEGER DEFAULT 1,  -- Condition must persist for X days
  forecast_window INTEGER DEFAULT 5,  -- Check next X days in forecast
  
  -- Alert Configuration
  severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
  alert_type VARCHAR(100) NOT NULL,
  priority INTEGER DEFAULT 5,  -- 1=highest, 10=lowest
  
  -- Messages
  message_en TEXT NOT NULL,
  recommendation_en TEXT NOT NULL,
  
  -- Disease/Risk Association
  diseases_at_risk TEXT[],  -- ['anthracnose', 'powdery_mildew']
  risk_score DECIMAL(3, 1),  -- 0.0 to 10.0
  
  -- Metadata
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_alert_rules_fruit_types ON public.alert_rules USING GIN(fruit_types);
CREATE INDEX idx_alert_rules_active ON public.alert_rules(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_alert_rules_severity ON public.alert_rules(severity);
CREATE INDEX idx_alert_rules_priority ON public.alert_rules(priority);

-- ============================================================================
-- MANGO ALERT RULES (Pakistan's #1 Export - Sindhri, Chaunsa, Anwar Ratol)
-- Critical Periods: Flowering (Jan-Feb), Fruit Setting (Mar-Apr), Harvest (May-Jul)
-- Based on scientific research: Anthracnose thrives at 20-30°C, >95% humidity, rainfall
-- ============================================================================

-- 1. MANGO: Anthracnose Critical Risk (Perfect Storm Conditions)
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  temperature_min, temperature_max, humidity_min, rainfall_min,
  consecutive_days, severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Mango Anthracnose Critical Outbreak',
  'MANGO_ANTHRACNOSE_CRITICAL',
  'Perfect conditions for Colletotrichum gloeosporioides: 20-30°C + >95% RH + rainfall. Spore germination and appressoria formation imminent.',
  ARRAY['mango'],
  ARRAY['flowering', 'fruiting'],
  20.0, 30.0, 95.0, 5.0,
  1, 'critical', 'disease_risk', 1,
  '🦠 ANTHRACNOSE CRITICAL ALERT: Perfect infection conditions detected! Temperature 20-30°C with >95% humidity and rainfall - spore germination and infection will occur within hours. This is Pakistan''s #1 cause of mango export rejection.',
  'EMERGENCY FUNGICIDE PROTOCOL: 1) Apply Copper Oxychloride (3g/L) + Mancozeb (2g/L) spray IMMEDIATELY (within 6 hours). 2) If rain is forecasted, spray BEFORE rain starts - post-rain spraying is 70% less effective. 3) Remove and BURN all infected plant material (leaves, twigs, mummified fruits) - do NOT compost. 4) Improve orchard drainage to reduce standing water. 5) Increase air circulation by pruning dense canopy areas. 6) Repeat fungicide application after 7-10 days if wet conditions persist. 7) Monitor for blossom blight and fruit drop during flowering period. 8) Disinfect all pruning tools with 10% bleach solution between cuts. NOTE: Infected fruits develop latent infections that only appear during ripening, causing post-harvest losses.',
  ARRAY['anthracnose', 'blossom_blight', 'fruit_rot', 'leaf_spot'],
  10.0
);

-- 2. MANGO: Anthracnose High Risk (Near-optimal conditions)
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  temperature_min, temperature_max, humidity_min, rainfall_min,
  consecutive_days, severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Mango Anthracnose High Risk Warning',
  'MANGO_ANTHRACNOSE_HIGH',
  'Favorable conditions approaching: 20-30°C + 80-95% humidity + light rainfall. Disease development likely.',
  ARRAY['mango'],
  ARRAY['flowering', 'fruiting'],
  20.0, 30.0, 80.0, 2.0,
  2, 'high', 'disease_risk', 2,
  '⚠️ ANTHRACNOSE HIGH RISK: Weather conditions are highly favorable for fungal infection. Temperature in optimal 20-30°C range with 80%+ humidity and rainfall expected for 2+ days.',
  'PREVENTIVE ACTIONS: 1) Prepare for fungicide application - have Copper Oxychloride and Mancozeb ready. 2) Scout orchard for early signs: small dark spots on leaves, flower blackening, or premature fruit drop. 3) Remove any visible infected material immediately. 4) Avoid overhead irrigation - use drip irrigation only. 5) If conditions worsen (humidity >95%), escalate to emergency protocol. 6) Pay special attention to flowering trees - blossom blight causes 40-60% yield loss. 7) Ensure proper spacing between trees for air movement.',
  ARRAY['anthracnose', 'blossom_blight'],
  8.5
);

-- 3. MANGO: Peak Sporulation Temperature Alert
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  temperature_min, humidity_min,
  consecutive_days, severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Mango Anthracnose Peak Sporulation',
  'MANGO_ANTHRAC_PEAK_TEMP',
  'Peak disease progression observed at 27°C minimum temperature with high humidity - maximum spore production phase.',
  ARRAY['mango'],
  ARRAY['all'],
  27.0, 85.0,
  1, 'high', 'disease_risk', 2,
  '🌡️ PEAK ANTHRACNOSE SPORULATION: Minimum temperature at 27°C with high humidity - fungus is at maximum spore production capacity. Existing infections will spread rapidly.',
  'INTENSIVE MONITORING REQUIRED: 1) Inspect orchard twice daily for new infection spots. 2) Focus on recently wetted areas (rain splash zones). 3) If any rainfall occurs in next 48 hours, apply protective fungicide immediately. 4) This temperature is ideal for rapid disease spread - expect visible symptoms within 3-5 days of infection. 5) Mark infected trees for intensive treatment. 6) Harvest any mature fruits early to avoid latent infections.',
  ARRAY['anthracnose'],
  8.0
);

-- 4. MANGO: Flowering Period Rainfall (Blossom Blight Risk)
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  rainfall_min, forecast_window,
  severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Mango Flowering Rain - Blossom Blight',
  'MANGO_FLOWER_RAIN_BLIGHT',
  'Rainfall during flowering (Jan-Feb) causes blossom blight and severe flower drop - major yield loss. Splashing water spreads anthracnose spores.',
  ARRAY['mango'],
  ARRAY['flowering'],
  5.0, 3,
  'critical', 'disease_risk', 1,
  '💧🌸 BLOSSOM BLIGHT ALERT: Rainfall forecasted during critical flowering period. Expect 40-60% flower drop and anthracnose blossom infection. Splashing water will spread fungal spores from infected material to healthy flowers.',
  'DAMAGE CONTROL PROTOCOL: 1) Unfortunately, rain damage to flowers CANNOT be prevented once rain occurs. 2) BEFORE rain (if possible): Apply protective fungicide (Bordeaux mixture 1% or Copper Oxychloride) to flowers. 3) AFTER rain stops (within 48 hours): Spray Bordeaux mixture (1%) to prevent secondary fungal infections on damaged flowers. 4) Remove and destroy blackened/infected flowers immediately. 5) Adjust yield expectations downward by 50% - plan for reduced harvest. 6) Focus protection efforts on remaining healthy flowers. 7) Ensure excellent drainage to prevent prolonged wetness. 8) This is why traditional Pakistani mango farming avoids January irrigation. NOTE: Flower infection leads to fruit infection later.',
  ARRAY['blossom_blight', 'anthracnose', 'flower_drop'],
  9.5
);

-- 5. MANGO: Extreme Heat Stress (40°C+)
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  temperature_min, consecutive_days, forecast_window,
  severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Mango Extreme Heat Alert',
  'MANGO_HEAT_CRITICAL',
  'Critical heat stress above 40°C causes fruit sunburn, flower drop, and reduced fruit quality. However, high temperatures (>30°C) and solar radiation inactivate anthracnose spores.',
  ARRAY['mango'],
  ARRAY['all'],
  40.0, 2, 5,
  'critical', 'extreme_temp', 1,
  '🔥 EXTREME HEAT ALERT: Temperature forecast shows 40°C+ for next 2 days - severe fruit sunburn and heat stress imminent. However, anthracnose spore activity will be suppressed by heat.',
  'HEAT PROTECTION MEASURES: 1) Apply shade nets (40-50% shade) on south and west-facing trees immediately. 2) Increase irrigation frequency - irrigate during early morning (6-8 AM) and evening (6-8 PM), NEVER during peak heat. 3) Spray kaolin clay solution (5%) on fruits to reflect sunlight and reduce fruit surface temperature. 4) Apply 10-15cm thick mulch layer around tree base to retain soil moisture. 5) If flowering, expect 30-40% flower drop - this is unavoidable. 6) Monitor fruits for sunburn symptoms: brown patches on sun-exposed side. 7) Consider early harvest of mature fruits before peak heat damage. 8) POSITIVE NOTE: High heat will significantly reduce anthracnose disease pressure.',
  ARRAY['fruit_sunburn', 'flower_drop', 'heat_stress'],
  9.0
);

-- 6. MANGO: Pre-Harvest Rain (Fruit Cracking & Latent Infection Activation)
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  rainfall_min, forecast_window,
  severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Mango Pre-Harvest Rain Alert',
  'MANGO_HARVEST_RAIN',
  'Rain within 7-10 days of harvest causes fruit cracking and activates latent anthracnose infections during ripening phase.',
  ARRAY['mango'],
  ARRAY['harvest'],
  15.0, 7,
  'critical', 'disease_risk', 1,
  '💧🥭 PRE-HARVEST RAIN WARNING: Heavy rain (15mm+) forecasted within 7 days of harvest. Critical risk of fruit cracking AND activation of dormant anthracnose infections that will appear during ripening/storage.',
  'EMERGENCY HARVEST PROTOCOL: 1) Harvest ALL fruits that are 75%+ mature IMMEDIATELY (within 24 hours before rain). 2) Use ethylene treatment (Ethrel 39% SL @ 1ml/L water) for controlled early ripening. 3) Handle harvested fruits carefully - any wounds will become anthracnose entry points. 4) Store in well-ventilated area with humidity control (60-70% RH). 5) Fruits that crack after rain are unmarketable - expect 30-50% loss if not harvested early. 6) Post-rain: Inspect all remaining fruits for cracks and anthracnose lesions (sunken black spots). 7) Apply post-harvest fungicide treatment (hot water + fungicide dip at 52°C for 5 minutes). 8) Separate any fruits showing symptoms immediately. NOTE: Latent anthracnose infections established during fruit development will become visible as fruit ripens.',
  ARRAY['fruit_cracking', 'anthracnose', 'post_harvest_rot'],
  9.5
);

-- 7. MANGO: Dry Weather Recovery Alert
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  humidity_max, rainfall_max, consecutive_days,
  severity, alert_type, priority,
  message_en, recommendation_en,
  risk_score
) VALUES (
  'Mango Dry Weather - Disease Suppression',
  'MANGO_DRY_WEATHER',
  'Extended dry period with low humidity - anthracnose becomes inactive and quiescent. Safe period for orchard operations.',
  ARRAY['mango'],
  ARRAY['all'],
  60.0, 0.0, 5,
  'low', 'weather_favorable', 5,
  '☀️ FAVORABLE CONDITIONS: Extended dry weather with low humidity. Anthracnose pathogen is now inactive/quiescent - this is the safest period for orchard operations and fruit development.',
  'OPTIMAL ACTIVITY PERIOD: 1) This is the BEST time for pruning - wounds will heal without fungal infection. 2) Safe to perform thinning operations. 3) Reduce protective fungicide sprays (save costs). 4) Focus on orchard sanitation: collect and burn all old infected material from ground. 5) Prepare irrigation systems for next wet period. 6) Scout and mark any chronic infection sources for removal. 7) Train workers on disease identification during low-pressure period. IMPORTANT: Disease will reactivate when favorable conditions (rain + humidity) return - maintain vigilance.',
  2.0
);

-- ============================================================================
-- CITRUS ALERT RULES (Kinnow, Sweet Orange, Grapefruit)
-- Pakistan is world's 3rd largest Kinnow producer
-- Critical: Citrus Canker is a quarantine disease - can halt exports
-- Black Spot is major quality issue
-- Based on research: Canker 25-30°C + >80% RH + wind-driven rain
-- ============================================================================

-- 8. CITRUS: Citrus Canker Critical Outbreak (Wind + Rain + Humidity)
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  temperature_min, temperature_max, humidity_min, rainfall_min, wind_speed_max,
  consecutive_days, severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Citrus Canker Critical - Wind-Driven Rain',
  'CITRUS_CANKER_CRITICAL',
  'QUARANTINE DISEASE ALERT: Perfect storm for Xanthomonas citri - 25-30°C + >80% humidity + wind-driven rain. Bacteria enter through wind wounds and natural openings.',
  ARRAY['citrus', 'orange', 'grapefruit'],
  ARRAY['all'],
  25.0, 30.0, 80.0, 3.0, 30.0,
  1, 'critical', 'disease_risk', 1,
  '🚨🌧️💨 CITRUS CANKER EMERGENCY: QUARANTINE DISEASE OUTBREAK CONDITIONS! Perfect infection scenario: Warm (25-30°C) + High Humidity (>80%) + Wind-Driven Rain. This bacterial disease can SHUT DOWN ALL citrus exports from Pakistan. Bacteria spreading through storm wounds and rain splash.',
  'IMMEDIATE QUARANTINE PROTOCOL: 1) Apply Copper Hydroxide bactericide (2-3g/L) within 12 hours - spray BEFORE storm if possible. 2) Scout orchard IMMEDIATELY after storm for raised brown lesions with yellow halos on leaves, fruits, or stems. 3) QUARANTINE and mark infected trees with RED TAPE - isolate from healthy trees. 4) Remove and BURN all infected material (do NOT compost or bury - bacteria survive in soil). 5) Disinfect ALL tools, equipment, shoes, and vehicles leaving orchard (10% bleach solution). 6) Report suspected infection to Agriculture Department within 24 hours - this is a NOTIFIABLE disease. 7) Apply protective copper sprays every 14-21 days during monsoon season. 8) Avoid orchard entry during wet/windy conditions - human movement spreads bacteria. 9) Wind + rain is the most dangerous combination - storm damage creates wounds that bacteria exploit. 10) If infection confirmed: entire orchard may be quarantined, affecting export certification. NOTE: Storms and monsoons spread this disease across orchards within hours through wind-driven rain.',
  ARRAY['citrus_canker', 'bacterial_infection', 'export_ban_risk'],
  10.0
);

-- 9. CITRUS: Citrus Canker High Risk (Favorable Conditions)
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  temperature_min, temperature_max, humidity_min,
  consecutive_days, severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Citrus Canker High Risk Warning',
  'CITRUS_CANKER_HIGH',
  'Favorable conditions for bacterial multiplication: warm + humid. Moist leaf surfaces promote infection.',
  ARRAY['citrus', 'orange', 'grapefruit'],
  ARRAY['all'],
  25.0, 30.0, 80.0,
  2, 'high', 'disease_risk', 2,
  '⚠️ CITRUS CANKER HIGH RISK: Temperature at ideal 25-30°C with >80% humidity for 2+ days. Bacterial multiplication accelerating on moist leaf surfaces. If wind or rain occurs, risk escalates to CRITICAL.',
  'PREVENTIVE ACTIONS: 1) Prepare copper bactericide sprays for rapid deployment. 2) Inspect new flush growth daily - young tissue is most susceptible. 3) Remove and destroy any suspicious lesions immediately. 4) Avoid overhead irrigation - use drip irrigation only. 5) Ensure tools are disinfected before ANY pruning. 6) Monitor weather closely - if wind speed increases or rain forecasted, apply protective spray immediately. 7) Young trees and nurseries are highest risk - prioritize protection. 8) Document any symptoms with photos for Agriculture Department inspection.',
  ARRAY['citrus_canker'],
  8.5
);

-- 10. CITRUS: Black Spot Critical Infection Period
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  temperature_min, temperature_max, humidity_min, rainfall_min,
  consecutive_days, severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Citrus Black Spot Critical Infection',
  'CITRUS_BLACKSPOT_CRITICAL',
  'Perfect conditions for Guignardia citricarpa: 20-28°C + >85% humidity + prolonged wetness (48-72h). Spores releasing from leaf litter.',
  ARRAY['citrus', 'orange', 'grapefruit'],
  ARRAY['fruiting', 'harvest'],
  20.0, 28.0, 85.0, 10.0,
  2, 'critical', 'disease_risk', 1,
  '🦠🍊 BLACK SPOT CRITICAL ALERT: Perfect infection conditions - Temperature 20-28°C + Very High Humidity (>85%) + Prolonged Rainfall. Extended leaf wetness (48-72 hours required) will trigger massive spore release from fallen leaf litter. Fruit quality will be severely compromised.',
  'URGENT FUNGICIDE PROTOCOL: 1) Apply protective fungicide (Copper Oxychloride 3g/L OR Benomyl 1g/L) IMMEDIATELY. 2) Target fruit surfaces thoroughly - this is a fruit cosmetic disease. 3) Remove fallen leaf litter from orchard floor - this is the primary spore source. 4) Ensure spray coverage on lower fruit that are closer to contaminated ground. 5) Repeat application every 14-21 days during wet periods. 6) Monitor for symptoms: hard dark spots on fruit surface (not raised like canker). 7) Warm nights with wet mornings (dew) = highest infection risk. 8) Infected fruits are unmarketable - export rejection guaranteed. 9) Disease is especially aggressive in subtropical areas with summer rains and high humidity cycles. 10) Focus on fruit protection from flowering through harvest.',
  ARRAY['black_spot', 'fruit_blemish', 'export_rejection'],
  9.5
);

-- 11. CITRUS: Black Spot Extended Wetness Alert
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  humidity_min, rainfall_min, consecutive_days,
  severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Citrus Black Spot - Prolonged Wetness',
  'CITRUS_BLACKSPOT_WETNESS',
  'Extended high humidity with frequent rainfall creating 48-72 hour leaf wetness periods - critical for Black Spot infection.',
  ARRAY['citrus', 'orange', 'grapefruit'],
  ARRAY['fruiting', 'harvest'],
  85.0, 5.0, 3,
  'high', 'disease_risk', 2,
  '💧 BLACK SPOT WETNESS WARNING: Prolonged wet conditions (3+ days) with >85% humidity creating the 48-72 hour leaf wetness period required for successful Guignardia citricarpa infection. Spore maturation and dispersal accelerating.',
  'INTENSIVE PROTECTION REQUIRED: 1) Apply protective fungicide if not already done. 2) Improve orchard drainage to reduce standing water and ground moisture. 3) Clear ground vegetation that holds moisture near fruit. 4) Remove weeds and debris that increase humidity in lower canopy. 5) Rain splash from ground to fruit is the primary infection pathway - maintain clean orchard floor. 6) Scout for symptoms on developing fruit - dark specks that enlarge to hard spots. 7) Wind-driven rain spreads spores over longer distances during storms. 8) Consider fruit bagging for premium export citrus. 9) Warm + rainy + humid = perfect disease triangle.',
  ARRAY['black_spot'],
  8.0
);

-- 12. CITRUS: Cold Damage Warning (Winter Frost)
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  temperature_max, consecutive_days,
  severity, alert_type, priority,
  message_en, recommendation_en,
  risk_score
) VALUES (
  'Citrus Cold Damage Alert',
  'CITRUS_FROST_WARNING',
  'Citrus is sensitive to cold - Punjab winter (Dec-Jan) can damage fruit quality and tree health below 5°C.',
  ARRAY['citrus', 'orange', 'grapefruit'],
  ARRAY['all'],
  5.0, 1,
  'high', 'extreme_temp', 2,
  '❄️ FROST WARNING: Temperature dropping below 5°C - Citrus cold damage imminent. Fruit quality degradation and potential tree damage expected (Punjab winter threat).',
  'FROST PROTECTION PROTOCOL: 1) Cover young trees (1-3 years old) with plastic sheets or frost blankets overnight - remove after sunrise. 2) Harvest ALL ripe and near-ripe fruits IMMEDIATELY - cold damages internal fruit quality even if skin looks normal. 3) Light small fires (smudge pots) around orchard perimeter before dawn - smoke and heat protect trees. 4) Irrigate orchard soil in evening before cold night - wet soil retains 4x more heat than dry soil. 5) Avoid irrigation in early morning when frost present. 6) Remove frost protection covers after sunrise to prevent overheating. 7) Inspect for damage: water-soaked spots on fruits, leaf bronzing, and leaf drop. 8) Young flush and flowers are most vulnerable - expect some damage. 9) Do NOT prune frost-damaged wood until spring - wait to see extent of damage.',
  7.5
);

-- 13. CITRUS/GRAPEFRUIT: Fruit Fly Peak Activity
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  temperature_min, temperature_max, humidity_min,
  consecutive_days, severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Citrus Fruit Fly Peak Season',
  'CITRUS_FRUITFLY_PEAK',
  'Peak Bactrocera zonata activity: 25-35°C + 50%+ humidity. Rapid population growth and fruit infestation expected.',
  ARRAY['citrus', 'orange', 'grapefruit'],
  ARRAY['fruiting', 'harvest'],
  25.0, 35.0, 50.0,
  3, 'medium', 'fruit_fly', 3,
  '🪰 FRUIT FLY PEAK ACTIVITY: Temperature 25-35°C with moderate-high humidity for 3+ days - perfect breeding conditions for Bactrocera zonata (oriental fruit fly). Expect major infestation in ripening fruits if no control measures taken.',
  'INTEGRATED PEST MANAGEMENT: 1) Install methyl eugenol pheromone traps (1 trap per 4 trees) - these attract and kill males. 2) Collect and DESTROY all fallen/damaged fruits DAILY - rotting fruit is prime breeding site. 3) Apply protein bait spray (GF-120 or similar) on border rows and heavily infested areas. 4) Harvest fruits at proper maturity - avoid overripe fruits which attract flies. 5) For premium fruits: use fruit fly-proof paper bags on developing fruits. 6) Monitor trap counts: >5 flies per trap per week = HIGH RISK, initiate intensive control. 7) Bury or burn infested fruits 60cm deep - do NOT leave in orchard. 8) Fruit fly larvae feed inside fruit making it unmarketable. 9) Major cause of post-harvest loss (20-40% without control). 10) Population explodes in warm humid weather - prevention is essential.',
  ARRAY['fruit_fly', 'post_harvest_loss', 'larvae_infestation'],
  7.0
);

-- ============================================================================
-- GUAVA ALERT RULES (Allahabad Safeda, Surahi)
-- Pakistan exports guava to Middle East
-- Fruit fly is major quality issue - warm humid weather triggers population explosion
-- Based on research: Fruit fly 25-35°C (peak 28-32°C) + 60-90% RH + rain-dry cycles
-- ============================================================================

-- 14. GUAVA: Fruit Fly Peak Breeding Conditions
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  temperature_min, temperature_max, humidity_min,
  consecutive_days, severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Guava Fruit Fly Peak Breeding',
  'GUAVA_FRUITFLY_PEAK',
  'Optimal fruit fly breeding: 28-32°C + 60-90% RH. Rapid population growth - very high activity in warm humid conditions.',
  ARRAY['guava'],
  ARRAY['fruiting', 'harvest'],
  28.0, 32.0, 60.0,
  2, 'critical', 'fruit_fly', 1,
  '🪰🍐 FRUIT FLY CRITICAL ALERT: Peak breeding temperature (28-32°C) with optimal humidity (60-90%) for 2+ days. Fruit fly population explosion imminent. Adult survival and egg viability at maximum. Guava orchards with continuous fruiting are especially vulnerable.',
  'INTENSIVE FRUIT FLY CONTROL: 1) Install pheromone traps IMMEDIATELY (methyl eugenol for male flies, 1 trap per 3-4 trees). 2) Apply protein bait spray (GF-120 NF Naturalyte) on tree canopy - attracts and kills adults. 3) Bag ALL developing fruits with newspaper or specialized fruit bags - this is MOST EFFECTIVE method. 4) Collect fallen fruits TWICE DAILY (morning and evening) - rotting fruits are prime breeding sites. 5) Bury collected fruits minimum 60cm deep OR burn immediately. 6) Remove overripe fruits from trees - harvest at proper maturity. 7) Maintain orchard cleanliness - no fruit debris on ground. 8) Monitor trap catches: >3 flies/trap/day = EMERGENCY LEVEL. 9) Adult flies lay eggs in soft ripening fruits - larvae feed inside making fruit unmarketable. 10) Without control, expect 40-60% fruit loss. 11) Continue trapping and sanitation for 2 weeks after last fruit harvest.',
  ARRAY['fruit_fly', 'larvae_infestation', 'fruit_loss'],
  9.5
);

-- 15. GUAVA: Fruit Fly Post-Rain Surge
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  temperature_min, temperature_max, rainfall_min, humidity_min,
  consecutive_days, severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Guava Fruit Fly Rain-to-Dry Cycle',
  'GUAVA_FRUITFLY_RAIN_DRY',
  'MOST DANGEROUS PATTERN: Light/moderate rain followed by warm dry weather - fruit fly population explodes. Common during monsoon fruiting season.',
  ARRAY['guava'],
  ARRAY['fruiting', 'harvest'],
  25.0, 35.0, 5.0, 60.0,
  1, 'critical', 'fruit_fly', 1,
  '🌧️☀️🪰 FRUIT FLY SURGE ALERT: Rain-to-dry cycle detected - THE MOST DANGEROUS PATTERN! Light rain followed by warm dry weather creates explosive fruit fly breeding conditions. This cycle is common during Pakistan''s monsoon fruiting season and causes massive infestations.',
  'EMERGENCY RESPONSE PROTOCOL: 1) This is the HIGHEST RISK scenario - immediate intensive action required. 2) New fruit flush from rain + warm dry weather = perfect breeding conditions. 3) Triple frequency of fruit collection - check orchard 3 times daily if possible. 4) Apply protein bait spray immediately after rain stops and ground dries. 5) Increase trap density temporarily (1 trap per 2 trees) during this critical 7-10 day period. 6) Bag ANY unbaged fruits immediately - even small fruits. 7) Scout for early infestation signs: small puncture marks on fruit skin, oozing sap. 8) Overlapping fruit sets in guava make it continuously vulnerable - no "safe" period. 9) Population can increase 10-fold within one week under these conditions. 10) This weather pattern repeats throughout monsoon - maintain constant vigilance.',
  ARRAY['fruit_fly', 'population_explosion'],
  10.0
);

-- 16. GUAVA: Anthracnose + Fruit Fly Combined Risk
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  temperature_min, temperature_max, humidity_min, rainfall_min,
  consecutive_days, severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Guava Combined Disease-Pest Alert',
  'GUAVA_DISEASE_PEST_COMBO',
  'DOUBLE THREAT: Conditions favor BOTH anthracnose disease AND fruit fly infestation. This combination causes 40-60% fruit loss.',
  ARRAY['guava'],
  ARRAY['fruiting', 'harvest'],
  28.0, 35.0, 65.0, 5.0,
  2, 'critical', 'disease_risk', 1,
  '🦠🪰 DOUBLE THREAT CRITICAL: Perfect conditions for BOTH guava anthracnose disease AND fruit fly infestation simultaneously. Temperature 28-35°C + High Humidity (>65%) + Rainfall. This deadly combination causes 40-60% total fruit loss if not aggressively managed.',
  'INTEGRATED DISEASE-PEST MANAGEMENT: FUNGICIDE: 1) Apply Carbendazim (1g/L) OR Copper Oxychloride (3g/L) for anthracnose control. 2) Ensure spray coverage on fruits and new growth. INSECTICIDE: 3) Apply protein bait spray (GF-120) for fruit flies - can mix with fungicide for efficiency. 4) Do NOT use fruit bags that have been wet - replace with dry bags after rain. SANITATION: 5) Remove diseased fruits immediately (anthracnose shows as dark sunken spots that rot fruit). 6) Collect fallen fruits twice daily - diseased fruits attract more fruit flies. 7) Bag healthy fruits with newspaper/specialized bags. MONITORING: 8) Inspect fruits daily for: a) Anthracnose: black spots, fruit rot, b) Fruit fly: puncture marks, larvae holes. ORCHARD HYGIENE: 9) Maintain maximum cleanliness - no fruit debris anywhere. 10) Improve air circulation by selective pruning. 11) Avoid overhead irrigation - use drip only. 12) Both problems worsen with poor orchard sanitation - cleanliness is critical. 13) Spray sequence: Fungicide first (morning), protein bait second (afternoon). 14) Continue treatments every 10-14 days during favorable weather.',
  ARRAY['anthracnose', 'fruit_fly', 'fruit_rot', 'combined_loss'],
  9.0
);

-- 17. GUAVA: Wilt Disease Risk (Prolonged Wetness)
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  rainfall_min, humidity_min, consecutive_days,
  severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Guava Wilt Disease Alert',
  'GUAVA_WILT_RISK',
  'Fusarium wilt risk: prolonged wet conditions (4+ days) with high humidity. Soil-borne fungus activated by waterlogging.',
  ARRAY['guava'],
  ARRAY['all'],
  25.0, 75.0, 4,
  'high', 'disease_risk', 2,
  '🌧️ GUAVA WILT WARNING: Prolonged wetness (4+ days) with >75% humidity increases Fusarium wilt disease risk. This soil-borne fungus attacks roots during waterlogging. Young trees (1-5 years) are most vulnerable.',
  'WILT PREVENTION MEASURES: 1) CRITICAL: Ensure excellent drainage - clear all drainage channels immediately. 2) Do NOT irrigate if soil is already saturated - wilt fungus thrives in waterlogged soil. 3) Apply Trichoderma bio-fungicide to soil around tree base (100g per tree) - this beneficial fungus suppresses Fusarium. 4) Add organic mulch (10-15cm) to improve soil structure and drainage. MONITORING: 5) Watch for early wilt symptoms: a) Yellowing of leaves (especially one-sided yellowing), b) Wilting despite adequate soil moisture, c) Brown discoloration of wood when bark scratched. WARNING SIGNS: 6) If tree shows wilt symptoms, it CANNOT be saved with fungicides. 7) Remove infected trees immediately - dig up entire root system. 8) BURN infected trees completely - do NOT compost. 9) Do NOT replant guava in same location for minimum 3 years - fungus persists in soil. 10) Drench soil in infected area with Trichoderma + Carbendazim before replanting. 11) Young trees die within 2-3 weeks of symptom appearance. 12) Mature trees may show gradual decline over months. 13) Prevention through drainage is ONLY effective control - no cure exists.',
  ARRAY['fusarium_wilt', 'root_rot', 'tree_death'],
  7.5
);

-- ============================================================================
-- CROSS-FRUIT RULES (Apply to all fruits)
-- ============================================================================

-- 11. ALL FRUITS: Extreme Wind Alert
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  wind_speed_max, forecast_window,
  severity, alert_type, priority,
  message_en, recommendation_en,
  risk_score
) VALUES (
  'Strong Wind Alert - All Fruits',
  'ALL_WIND_DAMAGE',
  'High winds cause fruit drop, branch damage, and spread diseases',
  ARRAY['all'],
  ARRAY['flowering', 'fruiting'],
  50.0, 3,
  'high', 'wind_alert', 3,
  '💨 Strong Wind Alert: Winds above 50 km/h forecasted - Fruit drop and mechanical damage expected',
  'WIND PREPARATION: 1) Harvest any near-mature fruits before wind arrives. 2) Stake young trees. 3) Remove dead branches that could fall. 4) After wind: collect fallen fruits (if edible, use for juice/processing). 5) Inspect for injuries that could allow disease entry. 6) Expect 10-20% fruit drop in severe winds.',
  7.5
);

-- 12. ALL FRUITS: Hailstorm Alert
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  rainfall_min, temperature_min, temperature_max,
  severity, alert_type, priority,
  message_en, recommendation_en,
  risk_score
) VALUES (
  'Hailstorm Risk Alert',
  'ALL_HAIL_RISK',
  'Hail causes severe fruit scarring and unmarketability',
  ARRAY['all'],
  ARRAY['fruiting', 'harvest'],
  20.0, 15.0, 25.0,
  'critical', 'extreme_weather', 1,
  '🧊 HAILSTORM RISK: Weather pattern indicates possible hail - Can destroy entire crop in minutes!',
  'HAIL PROTECTION (Limited options): 1) If possible, use hail nets (expensive, usually only for high-value crops). 2) Harvest mature fruits IMMEDIATELY. 3) After hail: Inspect damage - fruits with deep scars are unmarketable (use for juice). 4) Apply copper spray to prevent infection through wounds. 5) Document damage for insurance claims.',
  10.0
);

-- 13. ALL FRUITS: Monsoon Flood Warning
INSERT INTO public.alert_rules (
  rule_name, rule_code, description, fruit_types, growth_stages,
  rainfall_min, consecutive_days,
  severity, alert_type, priority,
  message_en, recommendation_en,
  diseases_at_risk, risk_score
) VALUES (
  'Monsoon Flooding Risk',
  'ALL_FLOOD_WARNING',
  'Prolonged heavy rain can cause flooding and waterlogging - Pakistan monsoon pattern',
  ARRAY['all'],
  ARRAY['all'],
  100.0, 3,
  'critical', 'rainfall', 2,
  '🌊 FLOOD WARNING: Monsoon rainfall exceeding 100mm over 3 days - Waterlogging and flooding risk',
  'FLOOD PREPAREDNESS: 1) Clear drainage channels NOW. 2) Harvest all harvestable fruits immediately. 3) If flooding occurs: trees can survive 24-48 hours of waterlogging, but >3 days = root death. 4) After flooding: DO NOT irrigate for 7-10 days. 5) Apply fungicides after water recedes (root rot risk). 6) Young trees (<3 years) most vulnerable.',
  ARRAY['root_rot', 'tree_death', 'nutrient_leaching'],
  9.5
);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_alert_rules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_alert_rules_timestamp
BEFORE UPDATE ON public.alert_rules
FOR EACH ROW
EXECUTE FUNCTION update_alert_rules_updated_at();

-- ============================================================================
-- Summary Statistics (UPDATED)
-- ============================================================================
-- Mango rules: 7 (Anthracnose Critical/High/Peak, Flowering Rain, Heat, Pre-harvest Rain, Dry Weather)
-- Citrus/Orange/Grapefruit rules: 6 (Canker Critical/High, Black Spot Critical/Wetness, Cold, Fruit Fly)
-- Guava rules: 4 (Fruit Fly Peak/Rain-Dry, Disease-Pest Combo, Wilt)
-- All fruits rules: 3 (Wind, Hail, Monsoon Flood)
-- Total: 20 research-based, Pakistan-specific alert rules
-- All rules based on peer-reviewed agricultural research and local conditions
-- ============================================================================
