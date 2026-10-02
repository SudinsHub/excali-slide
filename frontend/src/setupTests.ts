import '@testing-library/jest-dom';

// Mock window.matchMedia if not available in jsdom
if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}

// Mock FontFace and document.fonts for JSDOM
if (typeof window !== 'undefined') {
  if (!(window as any).FontFace) {
    (window as any).FontFace = class FontFace {
      family: string;
      source: string | ArrayBuffer | ArrayBufferView;
      descriptors: any;
      status: string = 'loaded';

      constructor(family: string, source: string | ArrayBuffer | ArrayBufferView, descriptors: any = {}) {
        this.family = family;
        this.source = source;
        this.descriptors = descriptors;
      }

      async load() {
        return this;
      }
    };
  }

  if (!document.fonts) {
    (document as any).fonts = {
      add: () => {},
      has: () => true,
      ready: Promise.resolve(),
      check: () => true,
      load: () => Promise.resolve([]),
      values: () => [][Symbol.iterator](),
    };
  }
}

// Mock HTMLCanvasElement.getContext so Excalidraw feature detection and text measurement succeeds in JSDOM
if (typeof HTMLCanvasElement !== 'undefined') {
  HTMLCanvasElement.prototype.getContext = ((type: string) => {
    return {
      filter: 'none',
      fillRect: () => {},
      clearRect: () => {},
      getImageData: () => ({ data: new Uint8ClampedArray(4) }),
      putImageData: () => {},
      createImageData: () => [],
      setTransform: () => {},
      drawImage: () => {},
      save: () => {},
      fillText: () => {},
      restore: () => {},
      beginPath: () => {},
      moveTo: () => {},
      lineTo: () => {},
      closePath: () => {},
      stroke: () => {},
      translate: () => {},
      scale: () => {},
      rotate: () => {},
      arc: () => {},
      fill: () => {},
      measureText: (text: string) => ({
        width: text.length * 10,
        actualBoundingBoxAscent: 10,
        actualBoundingBoxDescent: 10,
      }),
      transform: () => {},
      rect: () => {},
      clip: () => {},
    } as any;
  }) as any;

  HTMLCanvasElement.prototype.toBlob = (callback: BlobCallback) => {
    callback(new Blob([], { type: 'image/png' }));
  };
}
