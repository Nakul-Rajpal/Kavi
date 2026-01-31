import { useEffect, useState, useCallback, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import { supabase } from '../lib/supabaseClient'

// Custom emoji marker icon
const createPingIcon = () => {
  return L.divIcon({
    html: '<span style="font-size: 28px; filter: drop-shadow(1px 1px 2px rgba(0,0,0,0.5));">📍</span>',
    className: 'ping-marker',
    iconSize: [28, 28],
    iconAnchor: [14, 28],
    popupAnchor: [0, -28],
  })
}

const pingIcon = createPingIcon()

// Component to handle flying to new pings
function FlyToNewPing({ latestPing, shouldFly }) {
  const map = useMap()

  useEffect(() => {
    if (latestPing && shouldFly) {
      const currentZoom = map.getZoom()
      const targetZoom = Math.max(currentZoom, 16)
      map.flyTo([latestPing.lat, latestPing.lng], targetZoom, {
        duration: 1.5,
      })
    }
  }, [latestPing, shouldFly, map])

  return null
}

// Format timestamp for display
function formatTimestamp(timestamp) {
  return new Date(timestamp).toLocaleString()
}

export default function PingMap({ onStatusChange, onPingsUpdate }) {
  const [pings, setPings] = useState([])
  const [latestPing, setLatestPing] = useState(null)
  const [shouldFly, setShouldFly] = useState(false)
  const pingIdsRef = useRef(new Set())

  // Add a ping while avoiding duplicates
  const addPing = useCallback((newPing) => {
    if (pingIdsRef.current.has(newPing.id)) {
      return false
    }
    pingIdsRef.current.add(newPing.id)
    setPings((prev) => [...prev, newPing])
    return true
  }, [])

  // Fetch initial pings
  useEffect(() => {
    async function fetchInitialPings() {
      const { data, error } = await supabase
        .from('pings')
        .select('*')
        .order('created_at', { ascending: true })

      if (error) {
        console.error('Error fetching pings:', error)
        return
      }

      if (data && data.length > 0) {
        data.forEach((ping) => pingIdsRef.current.add(ping.id))
        setPings(data)
        setLatestPing(data[data.length - 1])
      }
    }

    fetchInitialPings()
  }, [])

  // Subscribe to realtime INSERT events
  useEffect(() => {
    const channel = supabase
      .channel('pings-realtime')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'pings',
        },
        (payload) => {
          console.log('New ping received:', payload.new)
          const newPing = payload.new
          const wasAdded = addPing(newPing)
          if (wasAdded) {
            setLatestPing(newPing)
            setShouldFly(true)
            // Reset shouldFly after animation
            setTimeout(() => setShouldFly(false), 2000)
          }
        }
      )
      .subscribe((status) => {
        console.log('Realtime subscription status:', status)
        if (status === 'SUBSCRIBED') {
          onStatusChange?.('connected')
        } else if (status === 'CLOSED' || status === 'CHANNEL_ERROR') {
          onStatusChange?.('disconnected')
        }
      })

    // Cleanup on unmount
    return () => {
      console.log('Cleaning up realtime subscription')
      supabase.removeChannel(channel)
    }
  }, [addPing, onStatusChange])

  // Notify parent of pings updates
  useEffect(() => {
    onPingsUpdate?.({ count: pings.length, latest: latestPing })
  }, [pings.length, latestPing, onPingsUpdate])

  // Default center: Amherst, MA
  const defaultCenter = [42.3736, -72.5199]
  const defaultZoom = 13

  return (
    <MapContainer
      center={defaultCenter}
      zoom={defaultZoom}
      style={{ height: '100%', width: '100%' }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      
      {pings.map((ping) => (
        <Marker key={ping.id} position={[ping.lat, ping.lng]} icon={pingIcon}>
          <Popup>
            <div className="ping-popup">
              <strong>Ping Details</strong>
              <p><span>Lat:</span> {ping.lat.toFixed(6)}</p>
              <p><span>Lng:</span> {ping.lng.toFixed(6)}</p>
              <p><span>Time:</span> {formatTimestamp(ping.created_at)}</p>
            </div>
          </Popup>
        </Marker>
      ))}
      
      <FlyToNewPing latestPing={latestPing} shouldFly={shouldFly} />
    </MapContainer>
  )
}

