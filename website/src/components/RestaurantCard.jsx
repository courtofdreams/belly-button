function Stars({ rating }) {
  const full = Math.floor(rating)
  const half = rating % 1 >= 0.5
  return (
    <span className="r-card-rating">
      {Array.from({ length: full }).map((_, i) => (
        <span key={i} className="r-star">★</span>
      ))}
      {half && <span className="r-star">½</span>}
      <span style={{ marginLeft: 3 }}>{rating}</span>
    </span>
  )
}

const IconPin = () => (
  <svg
    width="11"
    height="11"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    style={{ flexShrink: 0, marginTop: 2 }}
  >
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
    <circle cx="12" cy="10" r="3" />
  </svg>
)

const IconMap = () => (
  <svg
    width="11"
    height="11"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2.2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21" />
    <line x1="9" y1="3" x2="9" y2="18" />
    <line x1="15" y1="6" x2="15" y2="21" />
  </svg>
)

export default function RestaurantCard({ restaurant: r }) {
  return (
    <div className="r-card">
      {/* Image / gradient header */}
      <div
        className="r-card-img-placeholder"
        style={{ background: r.gradient }}
      >
        {r.emoji}
      </div>

      <div className="r-card-body">
        <div className="r-card-top">
          <div className="r-card-name">{r.name}</div>
          <div className="r-card-price">{r.price}</div>
        </div>

        <div className="r-card-meta">
          <Stars rating={r.rating} />
          <span className="r-card-cuisine">{r.cuisine}</span>
        </div>

        <div className="r-card-address">
          <IconPin />
          <span>{r.address}</span>
        </div>

        <p className="r-card-desc">{r.description}</p>

        <div className="r-card-footer">
          <div className="r-card-tags">
            {r.tags.slice(0, 2).map(tag => (
              <span key={tag} className="r-tag">{tag}</span>
            ))}
          </div>

          <a
            href={r.mapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="maps-btn"
          >
            <IconMap />
            Maps
          </a>
        </div>
      </div>
    </div>
  )
}
