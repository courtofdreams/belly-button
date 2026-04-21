import { useEffect, useRef } from "react";

export default function MapView({ results }) {
  const mapRef = useRef(null);

  useEffect(() => {
    if (!mapRef.current || !window.google || !results?.length) return;

    const first = results[0];
    console.log('Initializing map with results:', first);

    const map = new window.google.maps.Map(mapRef.current, {
      center: {
        lat: first.location.latitude,
        lng: first.location.longitude,
      },
      zoom: 13,
    });

    const bounds = new window.google.maps.LatLngBounds();

    results.forEach((item, index) => {
      if (!item.location) return;

      const position = {
        lat: item.location.latitude,
        lng: item.location.longitude,
      };

      new window.google.maps.Marker({
        position,
        map,
        label: String(index + 1),
        title: item.name,
      });

      bounds.extend(position);
    });

    map.fitBounds(bounds);
  }, [results]);

  return (
    <div
      ref={mapRef}
      style={{
        width: "100%",
        height: "320px",
        borderRadius: "16px",
        overflow: "hidden",
        marginBottom: "24px",
      }}
    />
  );
}