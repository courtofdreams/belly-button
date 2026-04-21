import { useState, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import ChatContainer from './components/ChatContainer'
import { generateResponse } from './utils/chatEngine'
import useAPI from './hooks/useAPI'
import { restaurants as restaurantsData} from './data/restaurants'

let nextId = 2

const extractCityFromAddress = (address) => {
  const parts = address.split(',')
  return parts.length >= 2 ? parts[parts.length - 3].trim() : 'Unknown'
}

const generateRandomGradient = () => {
  const color1 = Math.floor(Math.random() * 16777215).toString(16)
  const color2 = Math.floor(Math.random() * 16777215).toString(16)
  return `linear-gradient(135deg, #${color1}, #${color2})`
}

const generateEmojiForCuisine = (cuisine) => {
  const base = cuisine.toLowerCase().split(' ')[0] 
  const mapping = {
    italian: '🍝',
    japanese: '🍣',
    mexican: '🌮',
    chinese: '🍜',
    indian: '🍛',
    american: '🍔',
    thai: '🍜',
    french: '🥐',
    pizza: '🍕',
    mediterranean: '🥗',
    vegan: '🥦',
    vegetarian: '🥗',
    seafood: '🐟',
    sandwich: '🥪' ,
    'ice cream': '🍦',
  }
  return mapping[base] || '🍽️'
}

const parseRecommendationsResponse = (response) => {
  const results = []
  for (const item of response) {
    results.push({
      id: item.place_id,
      name: item.name,
      city: extractCityFromAddress(item.formattedAddress),
      cuisine: item.typeLabel || 'Restaurant',
      price: item.priceLevel || 'N/A',
      rating: item.rating || 'N/A',
      address: item.formattedAddress,
      description: item.reviewSummary?.text?.text || 'No description available.',
      emoji: generateEmojiForCuisine(item.typeLabel),
      gradient: generateRandomGradient(),
      // TODO: extract tags and dietary info from reviews or other fields if possible
      tags: [],
      dietary: [],
      occasion: ['dinner', 'lunch'],
      location: {
        latitude: item.location.latitude,
        longitude: item.location.longitude,
      },
      // TODO: Generate maps URL with actual coordinates
      mapsUrl: `https://maps.google.com/?q=${encodeURIComponent(item.name + ' ' + item.formattedAddress)}'`,
    })
  }
  return results;
}

export default function App() {
  const [conversations, setConversations] = useState([
    { id: 1, title: 'New Chat', messages: [] },
  ])
  const [activeId, setActiveId] = useState(1)
  const [isTyping, setIsTyping] = useState(false)
  const [loadingStatus, setLoadingStatus] = useState('Thinking…')
  const [context, setContext] = useState({})
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { fetchRecommendationsByKeyword } = useAPI()

  const activeConv = conversations.find(c => c.id === activeId)
  const messages = activeConv?.messages ?? []

  const appendAssistantMsg = useCallback((msg, convId) => {
    setConversations(prev =>
      prev.map(c =>
        c.id === convId ? { ...c, messages: [...c.messages, msg] } : c
      )
    )
  }, [])

  const sendMessage = useCallback(
    async (text, coords) => {
      const userMsg = { id: Date.now(), role: 'user', content: text }
      console.log('➡️ User message:', userMsg)
      console.log('   with context:', context)
      console.log('   with coordinates:', coords)
      const convId = activeId

      setConversations(prev =>
        prev.map(c =>
          c.id === convId
            ? {
              ...c,
              messages: [...c.messages, userMsg],
              title:
                c.messages.length === 0
                  ? text.slice(0, 42) + (text.length > 42 ? '…' : '')
                  : c.title,
            }
            : c
        )
      )

      setIsTyping(true)

      // ── Location-based: call real API ─────────────────────────────

        setLoadingStatus('Searching for recommendations..')

        try {
          const data = await fetchRecommendationsByKeyword(text);
          // const data = restaurantsData

          let restaurants = [];
          if (Array.isArray(data?.result)) {
            restaurants = parseRecommendationsResponse(data.result);
          }
          const count = Array.isArray(restaurants) ? restaurants.length : 0

          const assistantMsg = {
            id: Date.now() + 1,
            role: 'assistant',
            content: count > 0 ?
              `I found ${count} places Here are some of the best ones:` : "I couldn't find any restaurants near your location right now. Try a different radius or search by city name.",
            restaurants: Array.isArray(restaurants) ? restaurants : [],
            followUps: [
              'Show Italian restaurants nearby',
              'Filter by budget 💰',
              'Best-rated only ⭐',
              'Search a different city',
            ],
          }

          appendAssistantMsg(assistantMsg, convId)
        } catch (error) {
          console.error('Error fetching recommendations:', error)
          appendAssistantMsg(
            {
              id: Date.now() + 1,
              role: 'assistant',
              content:
                '⚠️ I had trouble reaching the restaurant service. Please try again, or search by city name instead.',
              restaurants: [],
              followUps: ['Try New York restaurants 🗽', 'Try San Francisco 🌉'],
            },
            convId
          )
        }

        setIsTyping(false)
        setLoadingStatus('Thinking…')
        // return


      // // ── Default: mock response ────────────────────────────────────
      // setLoadingStatus('Thinking…')
      // const delay = 1000 + Math.random() * 900

      // setTimeout(() => {
      //   const response = generateResponse(text, messages, context)

      //   appendAssistantMsg(
      //     {
      //       id: Date.now() + 1,
      //       role: 'assistant',
      //       content: response.text,
      //       restaurants: response.restaurants,
      //       followUps: response.followUps,
      //     },
      //     convId
      //   )

      //   setContext(response.updatedContext ?? {})
      //   setIsTyping(false)
      //   setLoadingStatus('Thinking…')
      // }, delay)
    },
    [activeId, messages, context, fetchRecommendationsByKeyword, appendAssistantMsg]
  )

  const newChat = useCallback(() => {
    const id = nextId++
    setConversations(prev => [
      ...prev,
      { id, title: 'New Chat', messages: [] },
    ])
    setActiveId(id)
    setContext({})
  }, [])

  const selectConv = useCallback((id) => {
    setActiveId(id)
    setContext({})
  }, [])

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={selectConv}
        onNewChat={newChat}
        isOpen={sidebarOpen}
      />
      <ChatContainer
        messages={messages}
        isTyping={isTyping}
        loadingStatus={loadingStatus}
        onSend={sendMessage}
        onToggleSidebar={() => setSidebarOpen(o => !o)}
      />
    </div>
  )
}
