-- Weather Database Schema
-- This script creates the tables for storing weather data from major cities worldwide

-- Cities table
CREATE TABLE IF NOT EXISTS cities (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    country_code VARCHAR(3) NOT NULL,
    latitude DECIMAL(10, 7) NOT NULL,
    longitude DECIMAL(10, 7) NOT NULL,
    population BIGINT,
    timezone VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, country_code)
);

-- Weather data table
CREATE TABLE IF NOT EXISTS weather_data (
    id SERIAL PRIMARY KEY,
    city_id INTEGER NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
    temperature_c DECIMAL(5, 2),
    temperature_f DECIMAL(5, 2),
    feels_like_c DECIMAL(5, 2),
    feels_like_f DECIMAL(5, 2),
    humidity INTEGER,
    pressure INTEGER,
    wind_speed DECIMAL(6, 2),
    wind_direction INTEGER,
    description VARCHAR(100),
    icon VARCHAR(20),
    visibility INTEGER,
    clouds INTEGER,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Weather forecast table (for multi-day forecasts)
CREATE TABLE IF NOT EXISTS weather_forecast (
    id SERIAL PRIMARY KEY,
    city_id INTEGER NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
    forecast_date DATE NOT NULL,
    temperature_min_c DECIMAL(5, 2),
    temperature_max_c DECIMAL(5, 2),
    temperature_min_f DECIMAL(5, 2),
    temperature_max_f DECIMAL(5, 2),
    humidity INTEGER,
    description VARCHAR(100),
    icon VARCHAR(20),
    pop DECIMAL(3, 2), -- Probability of precipitation
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(city_id, forecast_date)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_cities_location ON cities(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_cities_country ON cities(country_code);
CREATE INDEX IF NOT EXISTS idx_weather_data_city ON weather_data(city_id);
CREATE INDEX IF NOT EXISTS idx_weather_data_recorded ON weather_data(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_weather_forecast_city_date ON weather_forecast(city_id, forecast_date);

-- Insert major world cities
INSERT INTO cities (name, country, country_code, latitude, longitude, population, timezone) VALUES
    ('New York', 'United States', 'US', 40.7128, -74.0060, 8336817, 'America/New_York'),
    ('Los Angeles', 'United States', 'US', 34.0522, -118.2437, 3979576, 'America/Los_Angeles'),
    ('Chicago', 'United States', 'US', 41.8781, -87.6298, 2693976, 'America/Chicago'),
    ('Houston', 'United States', 'US', 29.7604, -95.3698, 2320268, 'America/Chicago'),
    ('Miami', 'United States', 'US', 25.7617, -80.1918, 467963, 'America/New_York'),
    ('London', 'United Kingdom', 'GB', 51.5074, -0.1278, 8982000, 'Europe/London'),
    ('Paris', 'France', 'FR', 48.8566, 2.3522, 2161000, 'Europe/Paris'),
    ('Berlin', 'Germany', 'DE', 52.5200, 13.4050, 3644826, 'Europe/Berlin'),
    ('Madrid', 'Spain', 'ES', 40.4168, -3.7038, 3223334, 'Europe/Madrid'),
    ('Rome', 'Italy', 'IT', 41.9028, 12.4964, 2860009, 'Europe/Rome'),
    ('Amsterdam', 'Netherlands', 'NL', 52.3676, 4.9041, 872757, 'Europe/Amsterdam'),
    ('Vienna', 'Austria', 'AT', 48.2082, 16.3738, 1897491, 'Europe/Vienna'),
    ('Moscow', 'Russia', 'RU', 55.7558, 37.6173, 12537954, 'Europe/Moscow'),
    ('Tokyo', 'Japan', 'JP', 35.6762, 139.6503, 13960000, 'Asia/Tokyo'),
    ('Beijing', 'China', 'CN', 39.9042, 116.4074, 21540000, 'Asia/Shanghai'),
    ('Shanghai', 'China', 'CN', 31.2304, 121.4737, 26320000, 'Asia/Shanghai'),
    ('Hong Kong', 'China', 'HK', 22.3193, 114.1694, 7496981, 'Asia/Hong_Kong'),
    ('Singapore', 'Singapore', 'SG', 1.3521, 103.8198, 5850342, 'Asia/Singapore'),
    ('Seoul', 'South Korea', 'KR', 37.5665, 126.9780, 9733509, 'Asia/Seoul'),
    ('Mumbai', 'India', 'IN', 19.0760, 72.8777, 20667656, 'Asia/Kolkata'),
    ('Delhi', 'India', 'IN', 28.6139, 77.2090, 16787941, 'Asia/Kolkata'),
    ('Bangkok', 'Thailand', 'TH', 13.7563, 100.5018, 10539000, 'Asia/Bangkok'),
    ('Dubai', 'United Arab Emirates', 'AE', 25.2048, 55.2708, 3331420, 'Asia/Dubai'),
    ('Istanbul', 'Turkey', 'TR', 41.0082, 28.9784, 15462452, 'Europe/Istanbul'),
    ('Sydney', 'Australia', 'AU', -33.8688, 151.2093, 5312163, 'Australia/Sydney'),
    ('Melbourne', 'Australia', 'AU', -37.8136, 144.9631, 5078193, 'Australia/Melbourne'),
    ('Auckland', 'New Zealand', 'NZ', -36.8509, 174.7645, 1657200, 'Pacific/Auckland'),
    ('São Paulo', 'Brazil', 'BR', -23.5505, -46.6333, 12325232, 'America/Sao_Paulo'),
    ('Rio de Janeiro', 'Brazil', 'BR', -22.9068, -43.1729, 6747815, 'America/Sao_Paulo'),
    ('Buenos Aires', 'Argentina', 'AR', -34.6037, -58.3816, 2891082, 'America/Argentina/Buenos_Aires'),
    ('Mexico City', 'Mexico', 'MX', 19.4326, -99.1332, 8855000, 'America/Mexico_City'),
    ('Lima', 'Peru', 'PE', -12.0464, -77.0428, 9751717, 'America/Lima'),
    ('Cairo', 'Egypt', 'EG', 30.0444, 31.2357, 20901000, 'Africa/Cairo'),
    ('Johannesburg', 'South Africa', 'ZA', -26.2041, 28.0473, 5635127, 'Africa/Johannesburg'),
    ('Lagos', 'Nigeria', 'NG', 6.5244, 3.3792, 14862000, 'Africa/Lagos'),
    ('Nairobi', 'Kenya', 'KE', -1.2921, 36.8219, 4397073, 'Africa/Nairobi'),
    ('Cape Town', 'South Africa', 'ZA', -33.9249, 18.4241, 433688, 'Africa/Johannesburg'),
    ('Toronto', 'Canada', 'CA', 43.6532, -79.3832, 2930000, 'America/Toronto'),
    ('Vancouver', 'Canada', 'CA', 49.2827, -123.1207, 675218, 'America/Vancouver'),
    ('Stockholm', 'Sweden', 'SE', 59.3293, 18.0686, 975904, 'Europe/Stockholm'),
    ('Copenhagen', 'Denmark', 'DK', 55.6761, 12.5683, 602481, 'Europe/Copenhagen'),
    ('Oslo', 'Norway', 'NO', 59.9139, 10.7522, 693494, 'Europe/Oslo'),
    ('Helsinki', 'Finland', 'FI', 60.1699, 24.9384, 656229, 'Europe/Helsinki'),
    ('Warsaw', 'Poland', 'PL', 52.2297, 21.0122, 1790658, 'Europe/Warsaw'),
    ('Prague', 'Czech Republic', 'CZ', 50.0755, 14.4378, 1309000, 'Europe/Prague'),
    ('Athens', 'Greece', 'GR', 37.9838, 23.7275, 664046, 'Europe/Athens'),
    ('Lisbon', 'Portugal', 'PT', 38.7223, -9.1393, 505526, 'Europe/Lisbon'),
    ('Dublin', 'Ireland', 'IE', 53.3498, -6.2603, 544107, 'Europe/Dublin'),
    ('Brussels', 'Belgium', 'BE', 50.8503, 4.3517, 185103, 'Europe/Brussels'),
    ('Zurich', 'Switzerland', 'CH', 47.3769, 8.5417, 402762, 'Europe/Zurich')
ON CONFLICT (name, country_code) DO NOTHING;

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for cities table
DROP TRIGGER IF EXISTS update_cities_updated_at ON cities;
CREATE TRIGGER update_cities_updated_at
    BEFORE UPDATE ON cities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- View for latest weather per city
CREATE OR REPLACE VIEW latest_weather AS
SELECT DISTINCT ON (c.id)
    c.id as city_id,
    c.name as city_name,
    c.country,
    c.country_code,
    c.latitude,
    c.longitude,
    c.population,
    c.timezone,
    w.temperature_c,
    w.temperature_f,
    w.feels_like_c,
    w.feels_like_f,
    w.humidity,
    w.pressure,
    w.wind_speed,
    w.wind_direction,
    w.description,
    w.icon,
    w.visibility,
    w.clouds,
    w.recorded_at
FROM cities c
LEFT JOIN weather_data w ON c.id = w.city_id
ORDER BY c.id, w.recorded_at DESC NULLS LAST;
