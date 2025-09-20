import { useContext, useEffect, useState, useRef } from "react";
import { SocketContext } from "../../contexts/socket.contexts";

interface CaptionItem {
  text: string;
  timestamp: number;
  isRemoving?: boolean;
}

export default function CaptionsPage() {
  const socket = useContext(SocketContext);
  const [captions, setCaptions] = useState<CaptionItem[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const timeoutRefs = useRef<Map<number, NodeJS.Timeout>>(new Map());

  // Fonction pour faire défiler vers le bas
  const scrollToBottom = () => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  };

  // Fonction pour supprimer un sous-titre après 5 secondes
  const removeCaption = (timestamp: number) => {
    // D'abord marquer comme en cours de suppression pour l'animation
    setCaptions((prev) =>
      prev.map((caption) =>
        caption.timestamp === timestamp
          ? { ...caption, isRemoving: true }
          : caption
      )
    );

    // Puis supprimer après l'animation (500ms)
    setTimeout(() => {
      setCaptions((prev) =>
        prev.filter((caption) => caption.timestamp !== timestamp)
      );
    }, 500);

    // Nettoyer le timeout
    const timeout = timeoutRefs.current.get(timestamp);
    if (timeout) {
      clearTimeout(timeout);
      timeoutRefs.current.delete(timestamp);
    }
  };

  // Scroll automatique quand de nouveaux sous-titres arrivent
  useEffect(() => {
    scrollToBottom();
  }, [captions]);

  useEffect(() => {
    socket.on("connect", () => {
      setIsConnected(true);
    });

    socket.on("disconnect", () => {
      setIsConnected(false);
    });

    socket.on("translation", (data: { text: string }) => {
      const timestamp = Date.now();
      const newCaption: CaptionItem = {
        text: data.text,
        timestamp: timestamp,
      };

      setCaptions((prev) => {
        const newCaptions = [...prev, newCaption];
        // Garder seulement les 5 derniers sous-titres pour éviter l'encombrement
        return newCaptions.slice(-5);
      });

      // Programmer la suppression après 10 secondes
      const timeout = setTimeout(() => {
        removeCaption(timestamp);
      }, 10000);

      timeoutRefs.current.set(timestamp, timeout);
    });

    return () => {
      socket.off("translation");
      socket.off("connect");
      socket.off("disconnect");

      // Nettoyer tous les timeouts
      timeoutRefs.current.forEach((timeout) => {
        clearTimeout(timeout);
      });
      timeoutRefs.current.clear();
    };
  }, [socket]);

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        margin: 0,
        padding: 0,
        fontFamily: "Arial, sans-serif",
        overflow: "hidden",
      }}
    >
      {/* Container principal des sous-titres */}
      <div
        ref={containerRef}
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "flex-end",
          padding: "20px",
          boxSizing: "border-box",
          overflowY: "auto",
        }}
      >
        {/* Fond translucide */}
        <div
          style={{
            backgroundColor: "rgba(0, 0, 0, 0.7)",
            borderRadius: "12px",
            padding: "20px 30px",
            backdropFilter: "blur(10px)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.3)",
            position: "relative",
          }}
        >
          {/* Indicateur de connexion */}
          <div
            style={{
              position: "absolute",
              top: "15px",
              right: "15px",
              zIndex: 1000,
            }}
          >
            <div
              style={{
                width: "12px",
                height: "12px",
                borderRadius: "50%",
                backgroundColor: isConnected ? "#10B981" : "#EF4444",
                boxShadow: "0 0 8px rgba(0, 0, 0, 0.5)",
              }}
            />
          </div>
          {captions.length === 0 ? (
            <div
              style={{
                color: "transparent",
                fontSize: "28px",
                textAlign: "center",
                fontStyle: "italic",
                minHeight: "40px",
                lineHeight: "1.4",
              }}
            >
              &nbsp;
            </div>
          ) : (
            <div
              style={{ display: "flex", flexDirection: "column", gap: "12px" }}
            >
              {captions.map((caption, index) => (
                <div
                  key={caption.timestamp}
                  style={{
                    color: "white",
                    fontSize: "32px",
                    lineHeight: "1.4",
                    fontWeight: "600",
                    textShadow: "3px 3px 6px rgba(0, 0, 0, 0.8)",
                    opacity: caption.isRemoving
                      ? 0
                      : index === captions.length - 1
                        ? 1
                        : 0.8,
                    transform:
                      index === captions.length - 1
                        ? "scale(1.02)"
                        : "scale(1)",
                    transition: "opacity 0.5s ease",
                  }}
                >
                  {caption.text}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
