import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { BlockTarget, StoryItem, StorySlide } from '../types';
import { SafeImage } from './SafeImage';
import { resolveMediaUrl } from '../utils/url';

function normalizeSlides(story: StoryItem): StorySlide[] {
  if (story.slides?.length) return story.slides;
  const slide: StorySlide = { duration: 5 };
  if (story.image) slide.image = story.image;
  if (story.target) slide.target = story.target;
  return slide.image || slide.text ? [slide] : [];
}

function useStoryNav() {
  const navigate = useNavigate();
  return useCallback(
    (target?: BlockTarget) => {
      if (!target) return;
      const { kind, value } = target;
      if (kind === 'category' && value) navigate(`/category/${value}`);
      else if (kind === 'item' && value) navigate(`/item/${value}`);
      else if (kind === 'tag' && value) navigate(`/?tag=${encodeURIComponent(value)}`);
      else if (kind === 'flash_sale') navigate('/sale');
      else if (kind === 'home') navigate('/');
      else if (kind === 'url' && value) window.open(value, '_blank', 'noopener,noreferrer');
    },
    [navigate],
  );
}

function StoryProgress({
  slides,
  storyIndex,
  slideIndex,
  progress,
}: {
  slides: StorySlide[];
  storyIndex: number;
  slideIndex: number;
  progress: number;
}) {
  return (
    <div className="story-viewer-progress">
      {slides.map((_, i) => (
        <div key={`${storyIndex}-${i}`} className="story-viewer-progress-seg">
          <div
            className="story-viewer-progress-fill"
            style={{
              width:
                i < slideIndex ? '100%' : i === slideIndex ? `${progress * 100}%` : '0%',
            }}
          />
        </div>
      ))}
    </div>
  );
}

export function StoryViewer({
  stories,
  startIndex,
  onClose,
}: {
  stories: StoryItem[];
  startIndex: number;
  onClose: () => void;
}) {
  const go = useStoryNav();
  const [storyIdx, setStoryIdx] = useState(startIndex);
  const [slideIdx, setSlideIdx] = useState(0);
  const [progress, setProgress] = useState(0);
  const [paused, setPaused] = useState(false);
  const touchStart = useRef<{ y: number; x: number } | null>(null);

  const story = stories[storyIdx];
  const slides = story ? normalizeSlides(story) : [];
  const current = slides[slideIdx];
  const durationMs = (current?.duration || 5) * 1000;

  const next = useCallback(() => {
    if (slideIdx < slides.length - 1) {
      setSlideIdx((s) => s + 1);
      setProgress(0);
      return;
    }
    if (storyIdx < stories.length - 1) {
      setStoryIdx((s) => s + 1);
      setSlideIdx(0);
      setProgress(0);
      return;
    }
    onClose();
  }, [slideIdx, slides.length, storyIdx, stories.length, onClose]);

  const prev = useCallback(() => {
    if (slideIdx > 0) {
      setSlideIdx((s) => s - 1);
      setProgress(0);
      return;
    }
    if (storyIdx > 0) {
      const prevStory = stories[storyIdx - 1];
      const prevSlides = normalizeSlides(prevStory);
      setStoryIdx((s) => s - 1);
      setSlideIdx(Math.max(0, prevSlides.length - 1));
      setProgress(0);
    }
  }, [slideIdx, storyIdx, stories]);

  useEffect(() => {
    if (!current || paused) return;
    const start = Date.now();
    const tick = setInterval(() => {
      const p = Math.min(1, (Date.now() - start) / durationMs);
      setProgress(p);
      if (p >= 1) {
        clearInterval(tick);
        next();
      }
    }, 50);
    return () => clearInterval(tick);
  }, [storyIdx, slideIdx, current, durationMs, paused, next]);

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  if (!story || !slides.length) return null;

  const handleTap = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    if (x < rect.width * 0.3) prev();
    else if (x > rect.width * 0.7) next();
    else setPaused((p) => !p);
  };

  return (
    <div
      className="story-viewer"
      role="dialog"
      aria-modal
      aria-label={story.title || 'استوری'}
    >
      <div className="story-viewer-top">
        <StoryProgress
          slides={slides}
          storyIndex={storyIdx}
          slideIndex={slideIdx}
          progress={progress}
        />
        <div className="story-viewer-head">
          <div className="flex items-center gap-2 min-w-0">
            <div className="story-viewer-avatar ring-2 ring-white/30">
              <SafeImage
                src={resolveMediaUrl(story.image || current.image || '')}
                className="h-full w-full object-cover"
                fallback={
                  <div className="flex h-full w-full items-center justify-center bg-white/20 text-xs">
                    {story.title?.slice(0, 2)}
                  </div>
                }
              />
            </div>
            <span className="truncate text-sm font-semibold text-white">{story.title}</span>
          </div>
          <button type="button" className="story-viewer-close" onClick={onClose} aria-label="بستن">
            ×
          </button>
        </div>
      </div>

      <div
        className="story-viewer-body"
        onClick={handleTap}
        onTouchStart={(e) => {
          touchStart.current = { y: e.touches[0].clientY, x: e.touches[0].clientX };
        }}
        onTouchEnd={(e) => {
          if (!touchStart.current) return;
          const dy = e.changedTouches[0].clientY - touchStart.current.y;
          if (dy > 80) onClose();
          touchStart.current = null;
        }}
      >
        {current.image ? (
          <SafeImage
            src={resolveMediaUrl(current.image)}
            className="story-viewer-media"
            fallback={<div className="story-viewer-media story-viewer-media--empty" />}
          />
        ) : (
          <div className="story-viewer-text-slide">
            <p>{current.text}</p>
          </div>
        )}
        {current.text && current.image && (
          <div className="story-viewer-caption">{current.text}</div>
        )}
        {paused && <div className="story-viewer-pause-hint">متوقف</div>}
      </div>

      {current.target && (
        <button
          type="button"
          className="story-viewer-cta"
          onClick={(e) => {
            e.stopPropagation();
            go(current.target);
            onClose();
          }}
        >
          مشاهده
        </button>
      )}
    </div>
  );
}

export function resolveStorySlides(story: StoryItem): StorySlide[] {
  return normalizeSlides(story);
}
