// Scroll-driven motion: Lenis smooth scroll + GSAP ScrollTrigger. Everything is skipped when the
// viewer prefers reduced motion. Hover feedback stays in CSS (colour and underline only).
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Lenis from 'lenis'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'

gsap.registerPlugin(ScrollTrigger)

export const reducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

let lenis: Lenis | null = null

export function startSmoothScroll() {
  if (reducedMotion()) {
    document.documentElement.classList.add('no-motion')
    return () => {}
  }
  lenis = new Lenis({ duration: 1.05, smoothWheel: true })
  lenis.on('scroll', ScrollTrigger.update)
  const tick = (time: number) => lenis?.raf(time * 1000)
  gsap.ticker.add(tick)
  gsap.ticker.lagSmoothing(0)
  return () => {
    gsap.ticker.remove(tick)
    lenis?.destroy()
    lenis = null
  }
}

export function scrollToTop() {
  if (lenis) lenis.scrollTo(0, { immediate: true })
  else window.scrollTo(0, 0)
}

/** Reveal every [data-reveal] element inside the ref as it scrolls into view. Elements that render later
 * (after data arrives) are picked up by a MutationObserver; each element is animated once and then stays visible. */
export function useReveal<T extends HTMLElement>(_deps: unknown[] = []) {
  // a callback ref, so the effect re-attaches if the page swaps its root element (e.g. loading -> content)
  const [root, ref] = useState<T | null>(null)
  useLayoutEffect(() => {
    if (!root) return
    const triggers: ScrollTrigger[] = []
    const show = (el: HTMLElement) => {
      el.style.opacity = '1'
      el.style.transform = 'none'
      el.dataset.revealed = '1'
    }
    const scan = () => {
      const items = Array.from(root.querySelectorAll<HTMLElement>('[data-reveal]:not([data-revealed]):not([data-pending])'))
      if (!items.length) return
      if (reducedMotion()) return items.forEach(show)
      items.forEach((el) => {
        el.dataset.pending = '1'
        const delay = Number(el.dataset.delay || 0)
        const st = ScrollTrigger.create({
          trigger: el,
          start: 'top 92%',
          once: true,
          onEnter: () =>
            gsap.to(el, { opacity: 1, y: 0, duration: 0.8, delay, ease: 'power3.out', onComplete: () => show(el) }),
        })
        triggers.push(st)
      })
      ScrollTrigger.refresh()
    }
    scan()
    const mo = new MutationObserver(() => scan())
    mo.observe(root, { childList: true, subtree: true })
    return () => {
      mo.disconnect()
      triggers.forEach((t) => t.kill())
      // anything still waiting is shown immediately, so nothing can be left invisible
      root.querySelectorAll<HTMLElement>('[data-pending]:not([data-revealed])').forEach((el) => {
        delete el.dataset.pending
        show(el)
      })
    }
  }, [root])
  return ref
}

/** Count a number up from zero the first time the element is visible. */
export function useCountUp(target: number | null | undefined, decimals = 0) {
  const ref = useRef<HTMLSpanElement>(null)
  const [text, setText] = useState(() => (target === null || target === undefined ? 'n/a' : target.toFixed(decimals)))
  useEffect(() => {
    if (target === null || target === undefined || Number.isNaN(target)) {
      setText('n/a')
      return
    }
    if (reducedMotion() || !ref.current) {
      setText(target.toFixed(decimals))
      return
    }
    const state = { v: 0 }
    const tween = gsap.to(state, {
      v: target,
      duration: 1.1,
      ease: 'power2.out',
      paused: true,
      onUpdate: () => setText(state.v.toFixed(decimals)),
    })
    const st = ScrollTrigger.create({ trigger: ref.current, start: 'top 92%', once: true, onEnter: () => tween.play() })
    return () => {
      st.kill()
      tween.kill()
    }
  }, [target, decimals])
  return { ref, text }
}

export { gsap, ScrollTrigger }

/** Grow [data-grow="x"|"y"] elements from zero along one axis when the container scrolls into view. */
export function useGrow<T extends HTMLElement>(deps: unknown[] = []) {
  const ref = useRef<T>(null)
  useLayoutEffect(() => {
    const root = ref.current
    if (!root || reducedMotion()) return
    const xs = Array.from(root.querySelectorAll<HTMLElement>('[data-grow="x"]'))
    const ys = Array.from(root.querySelectorAll<HTMLElement>('[data-grow="y"]'))
    const ctx = gsap.context(() => {
      if (xs.length)
        gsap.fromTo(xs, { scaleX: 0 }, { scaleX: 1, transformOrigin: 'left center', duration: 0.9, ease: 'power3.out', stagger: 0.025,
          scrollTrigger: { trigger: root, start: 'top 88%', once: true } })
      if (ys.length)
        gsap.fromTo(ys, { scaleY: 0 }, { scaleY: 1, transformOrigin: 'center bottom', duration: 0.9, ease: 'power3.out', stagger: 0.015,
          scrollTrigger: { trigger: root, start: 'top 88%', once: true } })
    }, root)
    return () => ctx.revert()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  return ref
}
