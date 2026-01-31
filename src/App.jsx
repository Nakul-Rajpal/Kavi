import { useState, useCallback } from 'react'
import PingMap from './components/PingMap'

function App() {
  const [connectionStatus, setConnectionStatus] = useState('connecting')
  const [pingInfo, setPingInfo] = useState({ count: 0, latest: null })

  const handleStatusChange = useCallback((status) => {
    setConnectionStatus(status)
  }, [])

  const handlePingsUpdate = useCallback((info) => {
    setPingInfo(info)
  }, [])

  const formatLatestPing = () => {
    if (!pingInfo.latest) return 'No pings yet'
    const { lat, lng, created_at } = pingInfo.latest
    const time = new Date(created_at).toLocaleTimeString()
    return `[${lat.toFixed(4)}, ${lng.toFixed(4)}] at ${time}`
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>Live Ping Map</h1>
          <div className="header-info">
            <div className={`status-indicator ${connectionStatus}`}>
              <span className="status-dot"></span>
              <span className="status-text">
                {connectionStatus === 'connected' ? 'Connected' : 
                 connectionStatus === 'connecting' ? 'Connecting...' : 'Disconnected'}
              </span>
            </div>
            <div className="ping-stats">
              <span className="ping-count">
                <strong>{pingInfo.count}</strong> ping{pingInfo.count !== 1 ? 's' : ''}
              </span>
              <span className="latest-ping" title={formatLatestPing()}>
                Latest: {formatLatestPing()}
              </span>
            </div>
          </div>
        </div>
      </header>
      
      <main className="map-container">
        <PingMap 
          onStatusChange={handleStatusChange} 
          onPingsUpdate={handlePingsUpdate}
        />
      </main>
    </div>
  )
}

export default App

