import { useState, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'

// Fix for default marker icons in Leaflet with bundlers
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

// @ts-expect-error - Leaflet internal
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

interface CityWeather {
  id: number
  name: string
  country: string
  country_code: string
  latitude: number
  longitude: number
  population: number | null
  timezone: string | null
  temperature_c: number | null
  temperature_f: number | null
  feels_like_c: number | null
  feels_like_f: number | null
  humidity: number | null
  pressure: number | null
  wind_speed: number | null
  wind_direction: number | null
  description: string | null
  icon: string | null
  clouds: number | null
  recorded_at: string | null
}

// Custom weather icon based on temperature
function getWeatherIcon(temp: number | null, icon: string | null): L.DivIcon {
  const emoji = icon || (temp === null ? '🌍' : 
    temp < 0 ? '❄️' : 
    temp < 10 ? '🥶' : 
    temp < 20 ? '🌤️' : 
    temp < 30 ? '☀️' : '🔥')
  
  const tempColor = temp === null ? '#888' :
    temp < 0 ? '#00bfff' :
    temp < 10 ? '#87ceeb' :
    temp < 20 ? '#90ee90' :
    temp < 30 ? '#ffd700' : '#ff4500'

  return L.divIcon({
    className: 'weather-marker',
    html: `
      <div class="marker-container" style="--temp-color: ${tempColor}">
        <div class="marker-icon">${emoji}</div>
        ${temp !== null ? `<div class="marker-temp">${Math.round(temp)}°</div>` : ''}
      </div>
    `,
    iconSize: [50, 60],
    iconAnchor: [25, 60],
    popupAnchor: [0, -60],
  })
}

// Component to handle map animations
function MapController({ selectedCity, onReset }: { 
  selectedCity: CityWeather | null
  onReset: () => void 
}) {
  const map = useMap()
  const initialView = useRef({ center: [20, 0] as [number, number], zoom: 2 })

  useEffect(() => {
    if (selectedCity) {
      map.flyTo([selectedCity.latitude, selectedCity.longitude], 10, {
        duration: 2,
        easeLinearity: 0.25,
      })
    }
  }, [selectedCity, map])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && selectedCity) {
        map.flyTo(initialView.current.center, initialView.current.zoom, {
          duration: 1.5,
        })
        onReset()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedCity, map, onReset])

  return null
}

// Weather detail panel
function WeatherPanel({ city, onClose, useCelsius }: { 
  city: CityWeather
  onClose: () => void
  useCelsius: boolean
}) {
  const temp = useCelsius ? city.temperature_c : city.temperature_f
  const feelsLike = useCelsius ? city.feels_like_c : city.feels_like_f
  const unit = useCelsius ? '°C' : '°F'

  const getWindDirection = (deg: number | null) => {
    if (deg === null) return 'N/A'
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    return directions[Math.round(deg / 45) % 8]
  }

  const formatTime = (isoString: string | null) => {
    if (!isoString) return 'N/A'
    return new Date(isoString).toLocaleString()
  }

  return (
    <div className="weather-panel">
      <button className="close-button" onClick={onClose} aria-label="Close">
        ×
      </button>
      
      <div className="panel-header">
        <span className="weather-emoji">{city.icon || '🌍'}</span>
        <div className="city-info">
          <h2>{city.name}</h2>
          <p className="country">{city.country}</p>
        </div>
      </div>

      <div className="temp-main">
        {temp !== null ? (
          <>
            <span className="temp-value">{Math.round(temp)}</span>
            <span className="temp-unit">{unit}</span>
          </>
        ) : (
          <span className="no-data">No data</span>
        )}
      </div>

      {city.description && (
        <p className="description">{city.description}</p>
      )}

      <div className="weather-details">
        <div className="detail-item">
          <span className="detail-icon">🌡️</span>
          <span className="detail-label">Feels like</span>
          <span className="detail-value">
            {feelsLike !== null ? `${Math.round(feelsLike)}${unit}` : 'N/A'}
          </span>
        </div>
        
        <div className="detail-item">
          <span className="detail-icon">💧</span>
          <span className="detail-label">Humidity</span>
          <span className="detail-value">
            {city.humidity !== null ? `${city.humidity}%` : 'N/A'}
          </span>
        </div>
        
        <div className="detail-item">
          <span className="detail-icon">💨</span>
          <span className="detail-label">Wind</span>
          <span className="detail-value">
            {city.wind_speed !== null 
              ? `${city.wind_speed} km/h ${getWindDirection(city.wind_direction)}`
              : 'N/A'
            }
          </span>
        </div>
        
        <div className="detail-item">
          <span className="detail-icon">🌡️</span>
          <span className="detail-label">Pressure</span>
          <span className="detail-value">
            {city.pressure !== null ? `${city.pressure} hPa` : 'N/A'}
          </span>
        </div>
        
        <div className="detail-item">
          <span className="detail-icon">☁️</span>
          <span className="detail-label">Clouds</span>
          <span className="detail-value">
            {city.clouds !== null ? `${city.clouds}%` : 'N/A'}
          </span>
        </div>
        
        {city.population && (
          <div className="detail-item">
            <span className="detail-icon">👥</span>
            <span className="detail-label">Population</span>
            <span className="detail-value">
              {city.population.toLocaleString()}
            </span>
          </div>
        )}
      </div>

      <div className="last-updated">
        Last updated: {formatTime(city.recorded_at)}
      </div>

      <p className="hint">Press ESC to return to world view</p>
    </div>
  )
}

// City list sidebar
function CityList({ cities, onSelect, selectedId, useCelsius }: {
  cities: CityWeather[]
  onSelect: (city: CityWeather) => void
  selectedId: number | null
  useCelsius: boolean
}) {
  const [search, setSearch] = useState('')
  
  const filteredCities = cities.filter(city => 
    city.name.toLowerCase().includes(search.toLowerCase()) ||
    city.country.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="city-list">
      <div className="search-box">
        <input
          type="text"
          placeholder="Search cities..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search cities"
        />
      </div>
      <div className="cities-scroll">
        {filteredCities.map(city => {
          const temp = useCelsius ? city.temperature_c : city.temperature_f
          return (
            <button
              key={city.id}
              className={`city-item ${selectedId === city.id ? 'selected' : ''}`}
              onClick={() => onSelect(city)}
            >
              <span className="city-icon">{city.icon || '🌍'}</span>
              <div className="city-details">
                <span className="city-name">{city.name}</span>
                <span className="city-country">{city.country}</span>
              </div>
              <span className="city-temp">
                {temp !== null ? `${Math.round(temp)}°` : '--'}
              </span>
            </button>
          )
        })}
        {filteredCities.length === 0 && (
          <p className="no-results">No cities found</p>
        )}
      </div>
    </div>
  )
}

function App() {
  const [cities, setCities] = useState<CityWeather[]>([])
  const [selectedCity, setSelectedCity] = useState<CityWeather | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [useCelsius, setUseCelsius] = useState(true)
  const [showList, setShowList] = useState(true)

  const fetchCities = async () => {
    try {
      const response = await fetch('/api/cities')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data: CityWeather[] = await response.json()
      setCities(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch weather data')
      console.error('Error fetching cities:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCities()
    // Refresh every 5 minutes
    const interval = setInterval(fetchCities, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  const handleCitySelect = (city: CityWeather) => {
    setSelectedCity(city)
  }

  const handleReset = () => {
    setSelectedCity(null)
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <button 
            className="toggle-list-btn"
            onClick={() => setShowList(!showList)}
            aria-label={showList ? 'Hide city list' : 'Show city list'}
          >
            {showList ? '◀' : '▶'}
          </button>
          <h1>🌍 World Weather</h1>
        </div>
        <div className="header-right">
          <div className="unit-toggle">
            <button
              className={!useCelsius ? 'active' : ''}
              onClick={() => setUseCelsius(false)}
            >
              °F
            </button>
            <button
              className={useCelsius ? 'active' : ''}
              onClick={() => setUseCelsius(true)}
            >
              °C
            </button>
          </div>
          <button className="refresh-btn" onClick={fetchCities} disabled={loading}>
            🔄 {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </header>

      {/* Error display */}
      {error && (
        <div className="error-banner">
          ⚠️ {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Main content */}
      <div className="main-content">
        {/* City list sidebar */}
        {showList && (
          <CityList
            cities={cities}
            onSelect={handleCitySelect}
            selectedId={selectedCity?.id || null}
            useCelsius={useCelsius}
          />
        )}

        {/* Map */}
        <div className="map-container">
          {loading && cities.length === 0 ? (
            <div className="loading-overlay">
              <div className="spinner"></div>
              <p>Loading weather data...</p>
            </div>
          ) : (
            <MapContainer
              center={[20, 0]}
              zoom={2}
              className="map"
              worldCopyJump={true}
              minZoom={2}
              maxBounds={[[-90, -180], [90, 180]]}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              
              <MapController 
                selectedCity={selectedCity} 
                onReset={handleReset}
              />
              
              {cities.map(city => (
                <Marker
                  key={city.id}
                  position={[city.latitude, city.longitude]}
                  icon={getWeatherIcon(city.temperature_c, city.icon)}
                  eventHandlers={{
                    click: () => handleCitySelect(city),
                  }}
                >
                  <Popup>
                    <div className="popup-content">
                      <strong>{city.name}</strong>
                      <br />
                      {city.country}
                      {city.temperature_c !== null && (
                        <>
                          <br />
                          {useCelsius 
                            ? `${Math.round(city.temperature_c)}°C`
                            : `${Math.round(city.temperature_f!)}°F`
                          }
                          {city.description && ` - ${city.description}`}
                        </>
                      )}
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
          )}
        </div>

        {/* Weather detail panel */}
        {selectedCity && (
          <WeatherPanel
            city={selectedCity}
            onClose={handleReset}
            useCelsius={useCelsius}
          />
        )}
      </div>
    </div>
  )
}

export default App
