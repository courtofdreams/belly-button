import { useState, useRef, useEffect, useContext } from 'react'

const IconSend = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <line x1="22" y1="2" x2="11" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
)

const IconLocation = () => (
  <svg
    width="15"
    height="15"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
    <circle cx="12" cy="10" r="3" />
  </svg>
)

export default function InputBar({ onSend, disabled }) {
  const [value, setValue] = useState('')
  const [locState, setLocState] = useState('idle') // idle | loading | done | error
  const textareaRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 130) + 'px'
  }, [value])

  const isNearbyIntent = (text) =>
    /near(by|me|\s*me)|(my\s+location|current\s+location)|restaurants?\s+near/i.test(text)

  const handleLocate = (text) => {
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
        onSend(text, { latitude, longitude })
        setTimeout(() => setLocState('idle'), 3000)
      },
      (error) => {
        console.error('❌ Geolocation error:', error.message)
        setLocState('error')
        setTimeout(() => setLocState('idle'), 3000)
      },
      { enableHighAccuracy: true, timeout: 10000 }
    )
  }

  const submit = () => {
    const text = value.trim()
    if (!text || disabled) return

    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    console.log('➡️ User input:', text)
    
    if (isNearbyIntent(text)) {
      handleLocate(text)
    } else {
      onSend(text)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const locLabel = {
    idle:    'Nearby',
    loading: 'Locating…',
    done:    'Located ✓',
    error:   'Denied ✗',
  }[locState]

  return (
    <div className="input-area">
      <div className="input-inner">
        <div className="input-box">
          <button
            className={`locate-btn locate-btn--${locState}`}
            onClick={() => handleLocate('Find restaurants nearby my location')}
            disabled={disabled || locState === 'loading'}
            aria-label="Find restaurants near me"
            title="Use my current location"
          >
            <IconLocation />
            <span>{locLabel}</span>
          </button>

          <div className="input-divider" />

          <textarea
            ref={textareaRef}
            className="chat-input"
            placeholder="Ask for restaurant recommendations…"
            value={value}
            onChange={e => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={disabled}
          />
          <button
            className="send-btn"
            onClick={submit}
            disabled={!value.trim() || disabled}
            aria-label="Send message"
          >
            <IconSend />
          </button>
        </div>
        <p className="input-hint">
          Belly Button uses mock data · Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
