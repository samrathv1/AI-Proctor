import { Camera, CameraType, CameraStatus } from '@/types';
import { mockCameras } from '@/data/mockCameras';
import { supabase, isSupabaseConfigured } from '@/lib/supabase/client';

let localCameras: Camera[] = [...mockCameras];

export const cameraService = {
  async getCameras(): Promise<Camera[]> {
    if (isSupabaseConfigured()) {
      try {
        const { data, error } = await supabase
          .from('cameras')
          .select(`
            id,
            name,
            camera_type,
            status,
            location,
            camera_sources (
              source_type,
              source_reference,
              resolution,
              fps
            )
          `);

        if (!error && data && data.length > 0) {
          return data.map((row: any) => {
            const src = Array.isArray(row.camera_sources) ? row.camera_sources[0] : row.camera_sources;
            return {
              id: row.id,
              name: row.name,
              type: row.camera_type as CameraType,
              status: row.status as CameraStatus,
              location: row.location,
              fps: src?.fps || 30,
              resolution: src?.resolution || '1080p (1920x1080)',
              latencyMs: row.camera_type === 'WEBCAM' ? 12 : 18,
              bitrate: '4.8 Mbps',
              url: src?.source_reference,
              lastPing: 'Just now',
              assignedExamId: 'exam-01',
            };
          });
        }
      } catch (err) {
        console.warn('Supabase getCameras failed, using local cameras:', err);
      }
    }

    await new Promise((r) => setTimeout(r, 100));
    return [...localCameras];
  },

  async connectCamera(payload: {
    type: CameraType;
    name?: string;
    url?: string;
    location?: string;
  }): Promise<Camera> {
    const camName = payload.name || `${payload.type} Feed`;
    const location = payload.location || 'Examination Hall 304';

    if (isSupabaseConfigured()) {
      try {
        const { data: cam, error } = await supabase
          .from('cameras')
          .insert({
            name: camName,
            camera_type: payload.type,
            status: 'ONLINE',
            location,
          })
          .select()
          .single();

        if (!error && cam) {
          await supabase.from('camera_sources').insert({
            camera_id: cam.id,
            source_type: payload.type === 'WEBCAM' ? 'WEBRTC' : 'RTSP_STREAM',
            source_reference: payload.url || 'webcam://device/0',
            resolution: '1080p (1920x1080)',
            fps: 30,
          });

          return {
            id: cam.id,
            name: cam.name,
            type: cam.camera_type,
            status: 'ONLINE',
            location: cam.location,
            fps: 30,
            resolution: '1080p (1920x1080)',
            latencyMs: payload.type === 'WEBCAM' ? 12 : 24,
            bitrate: '4.5 Mbps',
            url: payload.url,
            lastPing: 'Just now',
            assignedExamId: 'exam-01',
          };
        }
      } catch (err) {
        console.warn('Supabase connectCamera failed, using local store:', err);
      }
    }

    const newCamera: Camera = {
      id: `cam-${Date.now().toString().slice(-4)}`,
      name: camName,
      type: payload.type,
      status: 'ONLINE',
      location,
      fps: 30,
      resolution: '1080p (1920x1080)',
      latencyMs: payload.type === 'WEBCAM' ? 12 : 28,
      bitrate: '4.5 Mbps',
      url: payload.url || (payload.type === 'WEBCAM' ? 'webcam://active' : undefined),
      lastPing: 'Just now',
      assignedExamId: 'exam-01',
    };
    localCameras = [...localCameras, newCamera];
    return newCamera;
  },

  async disconnectCamera(id: string): Promise<boolean> {
    if (isSupabaseConfigured()) {
      try {
        await supabase
          .from('cameras')
          .update({ status: 'OFFLINE' })
          .eq('id', id);
      } catch (err) {
        console.warn('Supabase disconnectCamera failed:', err);
      }
    }
    localCameras = localCameras.map((cam) =>
      cam.id === id ? { ...cam, status: 'OFFLINE', fps: 0, bitrate: '0 Mbps' } : cam
    );
    return true;
  },

  async uploadVideoFeed(file: { name: string; size: number }): Promise<Camera> {
    const videoCamera: Camera = {
      id: `cam-vid-${Date.now().toString().slice(-4)}`,
      name: `Pre-recorded: ${file.name}`,
      type: 'VIDEO',
      status: 'ONLINE',
      location: 'Pre-recorded Exam Session',
      fps: 30,
      resolution: '1080p (1920x1080)',
      latencyMs: 5,
      bitrate: '6.0 Mbps',
      url: `blob://local/${file.name}`,
      lastPing: 'Just now',
      assignedExamId: 'exam-01',
    };

    if (isSupabaseConfigured()) {
      try {
        const { data: cam } = await supabase
          .from('cameras')
          .insert({
            name: videoCamera.name,
            camera_type: 'RECORDED_VIDEO',
            status: 'ONLINE',
            location: 'Pre-recorded Exam Session',
          })
          .select()
          .single();

        if (cam) {
          await supabase.from('camera_sources').insert({
            camera_id: cam.id,
            source_type: 'FILE_MP4',
            source_reference: `evidence-recordings/${file.name}`,
            resolution: '1080p (1920x1080)',
            fps: 30,
          });
          videoCamera.id = cam.id;
        }
      } catch (err) {
        console.warn('Supabase uploadVideoFeed failed, using local store:', err);
      }
    }

    localCameras = [videoCamera, ...localCameras];
    return videoCamera;
  },
};
