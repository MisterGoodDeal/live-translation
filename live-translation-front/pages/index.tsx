import { title } from "@/components/primitives";
import DefaultLayout from "@/layouts/default";
import {
  addToast,
  Button,
  Checkbox,
  Select,
  SelectItem,
  Slider,
  Textarea,
  ToastProvider,
} from "@heroui/react";
import { useContext, useEffect, useState, useRef } from "react";
import { SocketContext } from "../contexts/socket.contexts";
import { Microphone, MicrophonesResponse } from "../types/microphones";
import {
  SpeakerHighIcon,
  ClockCounterClockwiseIcon,
  ClockClockwiseIcon,
  WaveTriangleIcon,
  WaveSineIcon,
  StopIcon,
  PlayIcon,
  FloppyDiskBackIcon,
  GithubLogoIcon,
} from "@phosphor-icons/react";
import { SpeakerLowIcon } from "@phosphor-icons/react/dist/ssr";
import { ThemeSwitch } from "../components/theme-switch";

export default function IndexPage() {
  const [isLoading, setIsLoading] = useState(true);
  const socket = useContext(SocketContext);
  const [logs, setLogs] = useState<string[]>([]);
  const [translation, setTranslation] = useState<string[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const textareaLogsRef = useRef<HTMLTextAreaElement>(null);
  const textareaTranslationRef = useRef<HTMLTextAreaElement>(null);

  const [translationStarted, setTranslationStarted] = useState(false);

  const [microphones, setMicrophones] = useState<Microphone[]>([]);
  const [selectedMicrophone, setSelectedMicrophone] = useState<string>("");
  const [selectedModelWhisper, setSelectedModelWhisper] = useState<
    string | null
  >(null);
  const whipserModels = [
    {
      key: "small",
      label: "Small (CPU)",
    },
    {
      key: "medium",
      label: "Medium (GPU conseillé)",
    },
    {
      key: "large",
      label: "Large (GPU fortement recommandé)",
    },
  ];
  useEffect(() => {
    selectedModelWhisper &&
      socket.emit("update_config", { model_name: selectedModelWhisper });
    addToast({
      title: "Modèle Whisper mis à jour !",
      description: `Pour prendre effet, veuillez redémarrer l'application !`,
      color: "primary",
    });
  }, [selectedModelWhisper]);

  const [config, setConfig] = useState({
    model_name: "small",
    sample_rate: 16000,
    chunk_duration: 2,
    volume_threshold: 0.01,
    selected_microphone_id: null,
    use_gpu: false,
  });

  const saveConfigToLocalStorage = (newConfig: any) => {
    if (typeof window !== "undefined" && localStorage) {
      try {
        localStorage.setItem(
          "liveTranslationConfig",
          JSON.stringify(newConfig)
        );
      } catch (error) {
        console.error("Erreur lors de la sauvegarde de la config:", error);
      }
    }
  };

  const scrollToBottom = () => {
    if (textareaLogsRef.current) {
      textareaLogsRef.current.scrollTop = textareaLogsRef.current.scrollHeight;
    }
    if (textareaTranslationRef.current) {
      textareaTranslationRef.current.scrollTop =
        textareaTranslationRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs, translation]);

  useEffect(() => {
    const loadConfig = () => {
      if (typeof window !== "undefined" && localStorage) {
        const savedConfig = localStorage.getItem("liveTranslationConfig");
        if (savedConfig) {
          try {
            const config = JSON.parse(savedConfig);
            setSelectedModelWhisper(config.model_name || null);
            setSelectedMicrophone(
              config.selected_microphone_id
                ? config.selected_microphone_id.toString()
                : ""
            );
            setConfig(config);
          } catch (error) {
            console.error("Erreur lors du parsing de la config:", error);
          }
        }
        setIsLoading(false);
      } else {
        // Si localStorage n'est pas encore disponible, réessayer dans 100ms
        setTimeout(loadConfig, 100);
      }
    };

    loadConfig();
  }, []);

  useEffect(() => {
    console.log({ config });
    setSelectedModelWhisper(config.model_name || null);
  }, [config]);

  useEffect(() => {
    console.log({ socket });

    socket.on("pong", (data) => {
      addToast({
        title: "Handshake reçu !",
        color: "primary",
      });
      setIsConnected(true);
    });

    socket.on("logs", (data: { message: string }) => {
      const timestamp = new Date().toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });
      setLogs((prev) => {
        const newLogs = [...prev, `[${timestamp}] ${data.message}`];
        return newLogs.slice(-100);
      });
    });

    socket.on("translation", (data: { text: string }) => {
      setTranslation((prev) => [...prev, data.text]);
    });

    socket.on("translation_status", (data: { active: boolean }) => {
      setTranslationStarted(data.active);
      addToast({
        title: data.active
          ? "Transcription démarrée !"
          : "Transcription arrêtée !",
        color: data.active ? "success" : "warning",
      });
      setTranslation([]);
    });

    socket.on("connect", () => {
      setSelectedModelWhisper(null);
      addToast({
        title: "Connecté au serveur !",
        color: "success",
      });
      setIsConnected(true);
      socket.emit("get_microphones");
      socket.emit("get_config");
    });

    socket.on("disconnect", () => {
      setIsConnected(false);
      addToast({
        title: "Déconnecté du serveur !",
        color: "danger",
      });
    });

    socket.on("connect_error", () => {
      setIsConnected(false);
    });

    socket.on("microphones", (data: MicrophonesResponse) => {
      setMicrophones(data.microphones);
    });

    socket.on("config", (data) => {
      console.log("Configuration reçue:", data);
      setConfig(data);
      saveConfigToLocalStorage(data);

      if (data.selected_microphone_id !== null) {
        setSelectedMicrophone(data.selected_microphone_id.toString());
      }
    });

    return () => {
      socket.off("pong");
      socket.off("logs");
      socket.off("connect");
      socket.off("disconnect");
      socket.off("connect_error");
      socket.off("microphones");
      socket.off("config");
      socket.off("translation_status");
      socket.off("translation");
    };
  }, [socket]);

  const sendPing = () => {
    socket.emit("ping", { timestamp: Date.now() });
  };

  const handleConnect = () => {
    socket.connect();
  };

  const handleDisconnect = () => {
    socket.disconnect();
  };

  if (isLoading) {
    return (
      <DefaultLayout>
        <section className="flex flex-col items-center justify-center gap-4 py-8 md:py-10">
          <div className="text-center">
            <div className="text-lg">Chargement de la configuration...</div>
          </div>
        </section>
      </DefaultLayout>
    );
  }

  return (
    <DefaultLayout>
      <section className="flex flex-col items-center justify-center gap-4 py-8 md:py-10">
        <div className="inline-block max-w-xl text-center justify-center">
          <span className={title({ color: "violet" })}>Live</span>
          <span className={title()}>Translation</span>
        </div>

        <div className="flex flex-row gap-4 px-8 w-full">
          <div className="flex-1 p-4">
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-2">
                <div
                  className={`w-3 h-3 rounded-full ${isConnected ? "bg-green-500" : "bg-red-500"}`}
                ></div>
                <span className="text font-medium">
                  {isConnected
                    ? "Connecté au serveur"
                    : "Déconnecté du serveur"}
                </span>
              </div>
              <div className="flex flex-row gap-4">
                <Button
                  className="flex-1"
                  color="primary"
                  onPress={sendPing}
                  isDisabled={!isConnected}
                >
                  Ping Server
                </Button>
                <Button
                  className="flex-1"
                  color={isConnected ? "danger" : "primary"}
                  onPress={isConnected ? handleDisconnect : handleConnect}
                >
                  {isConnected ? "Déconnecter" : "Connecter"}
                </Button>
                <Button
                  className="flex-1"
                  color={translationStarted ? "danger" : "success"}
                  startContent={
                    translationStarted ? (
                      <StopIcon size={24} weight="fill" />
                    ) : (
                      <PlayIcon size={24} weight="fill" />
                    )
                  }
                  isDisabled={!isConnected}
                  onPress={() => {
                    translationStarted
                      ? socket.emit("stop_translation")
                      : socket.emit("start_translation");
                  }}
                >
                  {translationStarted ? "Arrêter" : "Démarrer"}
                </Button>
              </div>
              <Select
                size="sm"
                isDisabled={!isConnected}
                label="Modèle Whisper"
                isClearable={false}
                placeholder="Sélectionner un modèle Whisper"
                description={
                  "Modèle Whisper utilisé pour la traduction en direct"
                }
                selectedKeys={
                  selectedModelWhisper ? [selectedModelWhisper] : []
                }
                onSelectionChange={(keys) => {
                  const key = Array.from(keys)[0] as string;
                  setSelectedModelWhisper(key || "");
                  const newConfig = { ...config, model_name: key || "" };
                  saveConfigToLocalStorage(newConfig);
                }}
              >
                {whipserModels.map((model) => (
                  <SelectItem key={model.key}>{model.label}</SelectItem>
                ))}
              </Select>
              <Checkbox
                size="sm"
                isDisabled={!isConnected}
                isSelected={config.use_gpu}
                onValueChange={(checked) => {
                  const newConfig = { ...config, use_gpu: checked };
                  setConfig(newConfig);
                  saveConfigToLocalStorage(newConfig);
                  socket.emit("update_config", { use_gpu: checked });
                  addToast({
                    title: "Utilisation GPU mise à jour !",
                    description: `Pour prendre effet, veuillez redémarrer l'application !`,
                    color: "primary",
                  });
                }}
              >
                Utiliser l'accélération GPU pour les modèles Whisper
              </Checkbox>
              <div className="flex flex-row gap-4 justify-between items-start">
                <Select
                  size="sm"
                  isDisabled={!isConnected}
                  label="Liste des microphones"
                  isClearable={false}
                  placeholder="Sélectionner un microphone"
                  description={
                    "Microphone utilisé pour la traduction en direct"
                  }
                  selectedKeys={selectedMicrophone ? [selectedMicrophone] : []}
                  onSelectionChange={(keys) => {
                    const key = Array.from(keys)[0] as string;
                    setSelectedMicrophone(key || "");
                    const newConfig = {
                      ...config,
                      selected_microphone_id: key ? parseInt(key) : null,
                    };
                    saveConfigToLocalStorage(newConfig);
                  }}
                >
                  {microphones.map((microphone) => (
                    <SelectItem key={microphone.id.toString()}>
                      {`${microphone.name} (${microphone.channels} ${microphone.channels > 1 ? "canaux" : "canal"}, ${microphone.sample_rate}Hz)`}
                    </SelectItem>
                  ))}
                </Select>
                <Button
                  isIconOnly
                  aria-label="Save"
                  color="primary"
                  onPress={() => {
                    socket.emit("set_microphone", { id: +selectedMicrophone });
                    addToast({
                      title: "Microphone mis à jour !",
                      color: "success",
                    });
                  }}
                >
                  <FloppyDiskBackIcon />
                </Button>
              </div>
              <Slider
                isDisabled={!isConnected}
                defaultValue={config.sample_rate}
                startContent={<WaveTriangleIcon size={24} weight="fill" />}
                endContent={<WaveSineIcon size={24} weight="fill" />}
                getValue={(value) => `${value.toString()}Hz`}
                label="Échantillonage du micro"
                maxValue={48000}
                minValue={8000}
                step={100}
                value={config.sample_rate}
                onChange={(value: any) => {
                  const newConfig = { ...config, sample_rate: value };
                  setConfig(newConfig);
                  saveConfigToLocalStorage(newConfig);
                }}
                onChangeEnd={(value: any) => {
                  socket.emit("update_config", { sample_rate: value });
                }}
              />
              <Slider
                isDisabled={!isConnected}
                defaultValue={config.chunk_duration}
                startContent={
                  <ClockCounterClockwiseIcon size={24} weight="fill" />
                }
                endContent={<ClockClockwiseIcon size={24} weight="fill" />}
                formatOptions={{
                  style: "unit",
                  unit: "second",
                }}
                label="Durée du chunk"
                maxValue={5}
                minValue={0.1}
                step={0.1}
                value={config.chunk_duration}
                onChange={(value: any) => {
                  const newConfig = { ...config, chunk_duration: value };
                  setConfig(newConfig);
                  saveConfigToLocalStorage(newConfig);
                }}
                onChangeEnd={(value: any) => {
                  socket.emit("update_config", { chunk_duration: value });
                }}
              />
              <Slider
                isDisabled={!isConnected}
                defaultValue={config.volume_threshold}
                startContent={<SpeakerLowIcon size={24} weight="fill" />}
                endContent={<SpeakerHighIcon size={24} weight="fill" />}
                label="Seuil d'écoute du microphone"
                maxValue={0.5}
                minValue={0.01}
                step={0.01}
                value={config.volume_threshold}
                onChange={(value: any) => {
                  const newConfig = { ...config, volume_threshold: value };
                  setConfig(newConfig);
                  saveConfigToLocalStorage(newConfig);
                }}
                onChangeEnd={(value: any) => {
                  socket.emit("update_config", { volume_threshold: value });
                }}
              />
            </div>
          </div>
          <div className="flex-1 p-4 flex flex-col gap-4">
            <div className="flex flex-row gap-4 justify-end">
              <Button
                isIconOnly
                color="primary"
                onPress={() => {
                  window.open(
                    "https://github.com/MisterGoodDeal/live-translation-webserver",
                    "_blank"
                  );
                }}
              >
                <GithubLogoIcon size={24} weight="duotone" />
              </Button>
              <ThemeSwitch />
            </div>

            <Textarea
              ref={textareaLogsRef}
              className="w-full"
              label="Logs du serveur"
              placeholder="Aucun log reçu..."
              readOnly
              value={logs.join("\n")}
              minRows={20}
            />
            <Textarea
              ref={textareaTranslationRef}
              className="w-full"
              label="Transcription en direct"
              placeholder="Aucune transcription reçue..."
              readOnly
              value={translation.join("\n")}
              minRows={20}
            />
          </div>
        </div>
      </section>
      <ToastProvider />
    </DefaultLayout>
  );
}
