import { useEffect, useRef, useState, useContext } from 'react'
import Message from './Message'
import TypingIndicator from './TypingIndicator'
import InputBar from './InputBar'

const IconMenu = () => (
  <svg
    width="18"
    height="18"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <line x1="3" y1="6" x2="21" y2="6" />
    <line x1="3" y1="12" x2="21" y2="12" />
    <line x1="3" y1="18" x2="21" y2="18" />
  </svg>
)

const STARTER_PROMPTS = [
  'Ice cream shops in San Francisco 🍦',
  'Best ramen in San Francisco 🌉',
  'Romantic dinner in San Francisco 🌉',
]

export default function ChatContainer({
  messages,
  isTyping,
  loadingStatus,
  onSend,
  onToggleSidebar,
}) {
  const bottomRef = useRef(null)

  // Scroll to bottom on new messages or typing
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  return (
    <main className="chat-main">
      {/* Header */}
      <header className="chat-header">
        <button
          className="menu-btn"
          onClick={onToggleSidebar}
          aria-label="Toggle sidebar"
        >
          <IconMenu />
        </button>
        <span className="header-title">Belly Button</span>
        <span className="header-badge">Restaurant Guide</span>
      </header>

      {/* Messages */}
      <div className="messages-scroll">
        <div className="messages-inner">
          {messages.length === 0 ? (
            <EmptyState onPrompt={onSend} />
          ) : (
            messages.map(msg => (
              <Message key={msg.id} message={msg} onFollowUp={onSend} />
            ))
          )}

          {isTyping && <TypingIndicator status={loadingStatus} />}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <InputBar onSend={onSend} disabled={isTyping} />
    </main>
  )
}

function EmptyState({ onPrompt }) {
  const [locState, setLocState] = useState('idle') 

  const handleNearby = () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser.')
      return
    }

    setLocState('loading')

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords
        console.log('📍 User location obtained:')
        console.log('  Latitude: ', latitude)
        console.log('  Longitude:', longitude)
        console.log('  Full coords:', position.coords)
        setLocState('done')
        onPrompt('Find restaurants nearby my location', { latitude, longitude })
      },
      (error) => {
        console.error('❌ Geolocation error:', error.message)
        setLocState('error')
        setTimeout(() => setLocState('idle'), 3000)
      },
      { enableHighAccuracy: true, timeout: 10000 }
    )
  }

  return (
    <div className="empty-state">
      <div className="empty-icon">🍴</div>
      <h2>Find your next great meal</h2>
      <p>
        Tell me where you are, what you're craving, your budget, and the
        occasion — I'll find you the perfect restaurant.
      </p>

      {/* Nearby CTA */}
      {/* <button
        className={`nearby-btn nearby-btn--${locState}`}
        onClick={handleNearby}
        disabled={locState === 'loading'}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" />
        </svg>
        {{
          idle:    'Find Restaurants Nearby',
          loading: 'Getting your location…',
          done:    'Location found ✓',
          error:   'Location denied — try again',
        }[locState]}
      </button> */}

      <div className="chip-grid">
        {STARTER_PROMPTS.map(p => (
          <button
            key={p}
            className="starter-chip"
            onClick={() => onPrompt(p)}
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  )
}
