export interface MicrophonesResponse {
  microphones: Microphone[];
  count: number;
}

export type Microphone = {
  id: number;
  name: string;
  channels: number;
  sample_rate: number;
};
