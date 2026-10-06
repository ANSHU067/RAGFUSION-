import api, { getApiError } from './api';

const normalizeSource = (source) => ({
  id: source.id,
  videoId: source.video_id,
  url: source.url,
  title: source.title || `YouTube video (${source.video_id})`,
  channelName: source.channel_name || null,
  duration: source.duration_seconds || null,
  status:
    source.status === 'ready'
      ? 'completed'
      : source.status === 'failed'
      ? 'failed'
      : 'processing',
  transcriptLength: source.metadata?.transcript_characters || 0,
  chunks: source.metadata?.total_chunks || 0,
  progress:
    source.status === 'ready'
      ? 100
      : source.status === 'failed'
      ? 0
      : 20,
  createdAt: source.created_at,
  lastProcessed: source.updated_at,
  metadata: source.metadata || {},
});

export const youtubeApi = {
  async list() {
    const { data } = await api.get('/youtube');
    return data.items.map(normalizeSource);
  },

  async create(url) {
    let data;

    try {
      ({ data } = await api.post('/youtube/ingest', {
        url,
        languages: ['en'],
      }));
    } catch (error) {
      throw new Error(
        getApiError(error, 'Unable to add this YouTube video.'),
        { cause: error },
      );
    }

    return {
      id: data.youtube_source_id,
      videoId: data.video_id,
      url: data.url,
      title: data.title || `YouTube video (${data.video_id})`,
      channelName: data.channel_name || null,
      duration: null,
      status: data.status === 'ready' ? 'completed' : 'processing',
      transcriptLength: 0,
      chunks: data.total_chunks || 0,
      progress: data.status === 'ready' ? 100 : 20,
      createdAt: Date.now(),
      lastProcessed: Date.now(),
    };
  },

  async get(id) {
    const { data } = await api.get(`/youtube/${id}`);
    return normalizeSource(data);
  },

  async remove(id) {
    await api.delete(`/youtube/${id}`);
  },

  async getStatus(id) {
    return this.get(id);
  },

  async getTranscript(id) {
    const { data } = await api.get(`/youtube/${id}/transcript`);

    return {
      transcript: data.transcript || '',
      summary: data.summary || null,
    };
  },
};
