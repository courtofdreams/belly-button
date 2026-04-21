import ReactMarkdown from 'react-markdown'
import RestaurantCard from './RestaurantCard'
import MapView from './MapView'

export default function Message({ message, onFollowUp }) {
  const isUser = message.role === 'user'

  return (
    <div className={`msg-row ${isUser ? 'user' : 'assistant'}`}>
      <div className="msg-avatar">
        {isUser ? 'U' : '🍴'}
      </div>

      <div className="msg-body">
        <div className="msg-bubble">
          {isUser ? (
            <span>{message.content}</span>
          ) : (
            <ReactMarkdown>{message.content}</ReactMarkdown>
          )}
        </div>

        {/* Restaurant cards */}
        {!isUser && message.restaurants && message.restaurants.length > 0 && (
          <>
            <MapView results={message.restaurants} />
            <div className="cards-grid">
              {message.restaurants.map(r => (
                <RestaurantCard key={r.id} restaurant={r} />
              ))}
            </div>
          </>
        )}

        {/* Follow-up suggestion chips */}
        {!isUser && message.followUps && message.followUps.length > 0 && (
          <div className="followup-chips">
            {message.followUps.map(chip => (
              <button
                key={chip}
                className="followup-chip"
                onClick={() => onFollowUp(chip)}
              >
                {chip}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
