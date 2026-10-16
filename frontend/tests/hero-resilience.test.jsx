import { lazy, StrictMode, Suspense } from 'react'
import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { WebGLRenderer } from 'three'
import { HeroErrorBoundary } from '../src/components/common/HeroErrorBoundary'
import { HeroCanvas } from '../src/components/common/HeroCanvas'

vi.mock('@react-three/fiber', () => ({
  Canvas: ({ ref }) => <canvas ref={ref} data-testid="hero-canvas" />,
}))
vi.mock('three', () => ({
  ACESFilmicToneMapping: 4,
  WebGLRenderer: vi.fn(function () { this.dispose = vi.fn() }),
}))

beforeEach(() => {
  vi.spyOn(console, 'warn').mockImplementation(() => {})
  vi.spyOn(console, 'error').mockImplementation(() => {})
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({ isContextLost: () => false })
})
afterEach(() => { cleanup(); vi.restoreAllMocks() })

function Page({ children }) {
  return <><h1>Knowledge workspace</h1><HeroErrorBoundary>{children}</HeroErrorBoundary><a href="/signup">Get started</a></>
}

test('a scene render failure leaves the page and navigation usable', () => {
  function BrokenScene() { throw new Error('Renderer failed') }
  render(<Page><BrokenScene /></Page>)
  expect(screen.getByRole('img', { name: 'RAGFUSION knowledge core' })).toBeDefined()
  expect(screen.getByRole('heading', { name: 'Knowledge workspace' })).toBeDefined()
  expect(screen.getByRole('link', { name: 'Get started' }).getAttribute('href')).toBe('/signup')
})

test('a rejected lazy scene import is contained without retry loops', async () => {
  const load = vi.fn(() => Promise.reject(new Error('Chunk failed')))
  const Scene = lazy(load)
  await act(async () => {
    render(<Page><Suspense fallback={<p>Loading</p>}><Scene /></Suspense></Page>)
  })
  expect(screen.getByRole('img', { name: 'RAGFUSION knowledge core' })).toBeDefined()
  expect(load).toHaveBeenCalledTimes(1)
})

test.each([null, { isContextLost: () => true }])('unavailable or lost WebGL contexts use the gradient', (context) => {
  HTMLCanvasElement.prototype.getContext.mockReturnValue(context)
  render(<HeroCanvas antialias pixelRatio={1} />)
  expect(WebGLRenderer).not.toHaveBeenCalled()
  expect(screen.queryByTestId('hero-canvas')).toBeNull()
  expect(screen.getByRole('img', { name: 'RAGFUSION knowledge core' })).toBeDefined()
})

test('renderer constructor failure is handled before asynchronous configuration', () => {
  WebGLRenderer.mockImplementationOnce(function () { throw new Error('Driver failed') })
  render(<HeroCanvas antialias pixelRatio={1} />)
  expect(screen.getByRole('img', { name: 'RAGFUSION knowledge core' })).toBeDefined()
})

test('context loss switches to the gradient and removes listeners and GPU resources', () => {
  render(<HeroCanvas antialias pixelRatio={1} />)
  const canvas = screen.getByTestId('hero-canvas')
  const remove = vi.spyOn(canvas, 'removeEventListener')
  const renderer = WebGLRenderer.mock.instances.at(-1)
  const lost = new Event('webglcontextlost', { cancelable: true })
  act(() => { canvas.dispatchEvent(lost) })
  expect(lost.defaultPrevented).toBe(true)
  expect(screen.queryByTestId('hero-canvas')).toBeNull()
  expect(renderer.dispose).toHaveBeenCalledTimes(1)
  expect(remove).toHaveBeenCalledWith('webglcontextlost', expect.any(Function))
})

test('StrictMode and quality remounts clean up every renderer', () => {
  const view = render(<StrictMode><HeroCanvas key="high" antialias pixelRatio={2} /></StrictMode>)
  view.rerender(<StrictMode><HeroCanvas key="low" antialias={false} pixelRatio={1} /></StrictMode>)
  expect(screen.getByTestId('hero-canvas')).toBeDefined()
  view.unmount()
  for (const renderer of WebGLRenderer.mock.instances) expect(renderer.dispose).toHaveBeenCalledTimes(1)
})
