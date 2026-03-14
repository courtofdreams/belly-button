import { restaurants } from '../data/restaurants'

// ── Intent parsing ──────────────────────────────────────────────────
function parseIntent(text) {
  const msg = text.toLowerCase()
  const prefs = {}

  // Location
  const locationMap = {
    'new york': 'New York',
    'nyc': 'New York',
    'brooklyn': 'New York',
    'manhattan': 'New York',
    'san francisco': 'San Francisco',
    'sf': 'San Francisco',
    'bay area': 'San Francisco',
    'los angeles': 'Los Angeles',
    'la': 'Los Angeles',
    'hollywood': 'Los Angeles',
    'chicago': 'Chicago',
    'chi-town': 'Chicago',
    'miami': 'Miami',
    'south beach': 'Miami',
    'seattle': 'Seattle',
    'austin': 'Austin',
  }
  for (const [key, city] of Object.entries(locationMap)) {
    if (msg.includes(key)) {
      prefs.city = city
      break
    }
  }

  // Cuisine
  const cuisineMap = {
    italian: 'Italian',
    pizza: 'Italian',
    pasta: 'Italian',
    japanese: 'Japanese',
    sushi: 'Japanese',
    ramen: 'Japanese',
    'omakase': 'Japanese',
    mexican: 'Mexican',
    taco: 'Mexican',
    tacos: 'Mexican',
    burrito: 'Mexican',
    american: 'American',
    burger: 'American',
    burgers: 'American',
    bbq: 'American',
    'deep dish': 'American',
    thai: 'Thai',
    indian: 'Indian',
    french: 'French',
    chinese: 'Chinese',
    korean: 'Korean',
    peruvian: 'Peruvian',
    mediterranean: 'Mediterranean',
    asian: 'Asian',
  }
  for (const [key, cuisine] of Object.entries(cuisineMap)) {
    if (msg.includes(key)) {
      prefs.cuisine = cuisine
      break
    }
  }

  // Price
  if (msg.match(/cheap|budget|inexpensive|affordable|under \$20|low.cost/)) {
    prefs.price = '$'
  } else if (msg.match(/moderate|mid.range|reasonable|midrange/)) {
    prefs.price = '$$'
  } else if (msg.match(/fancy|upscale|fine dining|luxury|splurge|special occasion|michelin/)) {
    prefs.price = '$$$'
  } else if (msg.includes('$$$')) {
    prefs.price = '$$$'
  } else if (msg.includes('$$')) {
    prefs.price = '$$'
  }

  // Dietary
  prefs.dietary = []
  if (msg.match(/vegetarian|veggie/)) prefs.dietary.push('vegetarian')
  if (msg.match(/vegan/)) prefs.dietary.push('vegan')
  if (msg.match(/gluten.free|gluten free/)) prefs.dietary.push('gluten-free')
  if (msg.match(/halal/)) prefs.dietary.push('halal')
  if (msg.match(/kosher/)) prefs.dietary.push('kosher')

  // Occasion
  if (msg.match(/date|romantic|anniversary|valentine/)) prefs.occasion = 'date night'
  else if (msg.match(/quick|fast|grab|busy|on the go/)) prefs.occasion = 'quick lunch'
  else if (msg.match(/lunch/)) prefs.occasion = 'quick lunch'
  else if (msg.match(/group|party|celebration|birthday|friends/)) prefs.occasion = 'group dinner'
  else if (msg.match(/family|kids|children/)) prefs.occasion = 'family'
  else if (msg.match(/business|work|client|meeting|corporate/)) prefs.occasion = 'business'
  else if (msg.match(/brunch/)) prefs.occasion = 'brunch'
  else if (msg.match(/special/)) prefs.occasion = 'special occasion'

  return prefs
}

// ── Filtering ───────────────────────────────────────────────────────
function filterRestaurants(merged) {
  let results = [...restaurants]

  if (merged.city) {
    results = results.filter(r => r.city === merged.city)
  }

  if (merged.cuisine) {
    const c = merged.cuisine.toLowerCase()
    results = results.filter(r => r.cuisine.toLowerCase() === c)
  }

  if (merged.price) {
    results = results.filter(r => r.price === merged.price)
  }

  if (merged.dietary && merged.dietary.length > 0) {
    const wanted = merged.dietary
    results = results.filter(r =>
      wanted.some(d =>
        r.dietary.some(rd => rd.toLowerCase().includes(d.toLowerCase()))
      )
    )
  }

  if (merged.occasion) {
    const occasion = merged.occasion
    const occasionMatches = results.filter(r => r.occasion.includes(occasion))
    if (occasionMatches.length > 0) results = occasionMatches
  }

  // Sort by rating desc
  results.sort((a, b) => b.rating - a.rating)

  return results.slice(0, 4)
}

// ── Response text builder ───────────────────────────────────────────
function buildResponseText(merged, results) {
  if (results.length === 0) {
    const city = merged.city || 'the selected area'
    return (
      `I couldn't find restaurants matching **all** your criteria in **${city}**.\n\n` +
      `Try broadening your search — perhaps a different cuisine or price range? ` +
      `Or tell me a different city and I'll find something great!`
    )
  }

  const city = merged.city ? `**${merged.city}**` : 'your area'
  const cuisine = merged.cuisine ? `${merged.cuisine} ` : ''
  const priceLabel = merged.price
    ? ` in the **${merged.price}** price range`
    : ''
  const occasionLabel = merged.occasion
    ? ` perfect for **${merged.occasion}**`
    : ''

  let text =
    `Here are my top **${cuisine}picks** in ${city}${priceLabel}${occasionLabel}:\n\n`

  results.forEach((r, i) => {
    text += `**${i + 1}. ${r.name}** — ${r.cuisine} · ${r.price} · ⭐ ${r.rating}\n`
  })

  text +=
    `\nI've found **${results.length}** great option${results.length > 1 ? 's' : ''} for you. ` +
    `Each card below has details, ratings, and a direct link to Google Maps. Want to refine the search?`

  return text
}

// ── Follow-up suggestions ───────────────────────────────────────────
function buildFollowUps(merged, results) {
  const chips = []

  if (!merged.price) {
    chips.push('Show budget options 💰')
    chips.push('Show upscale options ✨')
  }
  if (!merged.occasion && results.length > 0) {
    chips.push('Best for date night 🥂')
    chips.push('Good for a group 🎉')
  }
  if (merged.cuisine) {
    chips.push(`More ${merged.cuisine} options`)
  } else {
    chips.push('Show Italian restaurants 🍝')
    chips.push('Show Japanese restaurants 🍣')
  }
  if (!merged.dietary || !merged.dietary.includes('vegetarian')) {
    chips.push('Show vegetarian options 🥗')
  }
  if (!merged.city) {
    chips.push('Restaurants in New York 🗽')
    chips.push('Restaurants in San Francisco 🌉')
  }

  return chips.slice(0, 4)
}

// ── Main export ─────────────────────────────────────────────────────
export function generateResponse(userMessage, chatHistory = [], context = {}) {
  const isGreeting = /^(hi|hello|hey|good\s|howdy|sup\b)/i.test(
    userMessage.trim()
  )
  const isFirstMessage = chatHistory.length === 0

  // Welcome message
  if (isGreeting || isFirstMessage) {
    return {
      text:
        "Hello! I'm **Belly Button** 🍴 — your personal restaurant guide.\n\n" +
        'I can help you find the perfect restaurant based on your:\n' +
        '- 📍 **Location** — city or neighborhood\n' +
        '- 🍜 **Cuisine** — Italian, Japanese, Mexican, and more\n' +
        '- 💰 **Budget** — $, $$, or $$$\n' +
        '- 🥗 **Dietary needs** — vegetarian, vegan, gluten-free\n' +
        '- 🎉 **Occasion** — date night, quick lunch, group dinner\n\n' +
        'Where are you dining and what are you in the mood for?',
      restaurants: [],
      followUps: [
        'Best restaurants in New York 🗽',
        'Romantic dinner in San Francisco 🌉',
        'Budget ramen in Chicago 🍜',
        'Vegan options in Los Angeles 🥑',
      ],
      updatedContext: {},
    }
  }

  const prefs = parseIntent(userMessage)
  const merged = { ...context, ...prefs }

  // If dietary arrays, merge them
  if (context.dietary && prefs.dietary) {
    merged.dietary = [...new Set([...context.dietary, ...prefs.dietary])]
  }

  const results = filterRestaurants(merged)

  // If no prefs detected and no context, nudge user
  if (
    !merged.city &&
    !merged.cuisine &&
    !merged.price &&
    (!merged.dietary || merged.dietary.length === 0) &&
    !merged.occasion
  ) {
    return {
      text:
        "I'd love to help! To give you the best recommendations, could you tell me:\n\n" +
        '- 🌆 **Which city** are you in? (New York, SF, LA, Chicago, Miami, Seattle)\n' +
        '- 🍽️ **What type of food** are you craving?\n' +
        '- 💸 **What\'s your budget?** ($, $$, $$$)\n\n' +
        "For example: *\"I want budget-friendly tacos in LA\"* or *\"romantic Italian in New York\"*",
      restaurants: [],
      followUps: [
        'Best restaurants in New York 🗽',
        'Cheap eats in Chicago 🍕',
        'Date night in Los Angeles 🥂',
        'Vegetarian options in Seattle 🌲',
      ],
      updatedContext: merged,
    }
  }

  const text = buildResponseText(merged, results)
  const followUps = buildFollowUps(merged, results)

  return {
    text,
    restaurants: results,
    followUps,
    updatedContext: merged,
  }
}
