import React from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import App from './App'

const state = vi.hoisted(() => ({ rooms: [] }))

vi.mock('livekit-client', async () => {
  const { EventEmitter } = await import('node:events')
  return {
    Room: class extends EventEmitter {
      constructor() {
        super()
        this.name = state.roomName || 'pilot-room'
        this.connect = vi.fn(state.connect || (async () => {}))
        this.localParticipant = {
          setMicrophoneEnabled: vi.fn(state.microphone || (async () => {})),
        }
        this.disconnect = vi.fn(async () => this.emit('disconnected'))
        state.rooms.push(this)
      }
    },
  }
})

function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}

function connect() {
  fireEvent.change(screen.getByPlaceholderText('wss://your-project.livekit.cloud'), {
    target: { value: 'wss://test.example' },
  })
  fireEvent.change(screen.getByPlaceholderText('my-training-room'), {
    target: { value: 'pilot-room' },
  })
  fireEvent.change(screen.getByPlaceholderText('Paste your LiveKit access token here'), {
    target: { value: 'fixture-token' },
  })
  fireEvent.click(screen.getByRole('button', { name: /Connect & Start Session/ }))
  return state.rooms.at(-1)
}

beforeEach(() => {
  state.rooms = []
  state.connect = null
  state.microphone = null
  state.roomName = null
  vi.spyOn(window, 'alert').mockImplementation(() => {})
  vi.spyOn(console, 'error').mockImplementation(() => {})
})

afterEach(cleanup)

describe('room lifecycle', () => {
  it('disconnects after microphone denial and allows a clean retry', async () => {
    state.microphone = async () => { throw new Error('Microphone denied') }
    render(<App />)
    const failedRoom = connect()
    await waitFor(() => expect(window.alert).toHaveBeenCalledWith('Connection failed: Microphone denied'))
    expect(failedRoom.disconnect).toHaveBeenCalled()
    state.microphone = null
    const retry = connect()
    await screen.findByText(/Session Active/)
    expect(retry).not.toBe(failedRoom)
    expect(retry.localParticipant.setMicrophoneEnabled).toHaveBeenCalledWith(true)
  })

  it('releases the room after a rejected token', async () => {
    state.connect = async () => { throw new Error('Token expired') }
    render(<App />)
    const room = connect()
    await waitFor(() => expect(window.alert).toHaveBeenCalledWith('Connection failed: Token expired'))
    expect(room.disconnect).toHaveBeenCalled()
    expect(room.localParticipant.setMicrophoneEnabled).not.toHaveBeenCalled()
  })

  it('preserves transcripts received before microphone setup finishes', async () => {
    const microphone = deferred()
    state.microphone = () => microphone.promise
    render(<App />)
    const room = connect()
    await waitFor(() => expect(room.localParticipant.setMicrophoneEnabled).toHaveBeenCalled())
    act(() => {
      room.emit('dataReceived', new TextEncoder().encode(JSON.stringify({
        type: 'transcript', role: 'agent', text: 'Early greeting',
      })))
    })
    await act(async () => microphone.resolve())
    expect(screen.getByText('Early greeting')).toBeTruthy()
    expect(screen.getByText(/Connected to room: pilot-room/)).toBeTruthy()
  })

  it('does not start a microphone when connection completes after unmount', async () => {
    const pending = deferred()
    state.connect = () => pending.promise
    const view = render(<App />)
    const room = connect()
    view.unmount()
    await act(async () => pending.resolve())
    expect(room.disconnect).toHaveBeenCalled()
    expect(room.localParticipant.setMicrophoneEnabled).not.toHaveBeenCalled()
    expect(window.alert).not.toHaveBeenCalled()
  })

  it('disconnects again if pending microphone setup finishes after unmount', async () => {
    const microphone = deferred()
    state.microphone = () => microphone.promise
    const view = render(<App />)
    const room = connect()
    await waitFor(() => expect(room.localParticipant.setMicrophoneEnabled).toHaveBeenCalled())
    view.unmount()
    const cleanupCalls = room.disconnect.mock.calls.length
    await act(async () => microphone.resolve())
    expect(room.disconnect.mock.calls.length).toBeGreaterThan(cleanupCalls)
  })

  it('ignores disconnection events from a previous session', async () => {
    render(<App />)
    const oldRoom = connect()
    await screen.findByText(/Session Active/)
    fireEvent.click(screen.getByRole('button', { name: /End Session/ }))
    await screen.findByRole('button', { name: /Connect & Start Session/ })
    const newRoom = connect()
    await screen.findByText(/Session Active/)
    act(() => oldRoom.emit('disconnected'))
    expect(screen.getByText(/Session Active/)).toBeTruthy()
    expect(newRoom.disconnect).not.toHaveBeenCalled()
  })

  it('rejects a token for a different room before publishing audio', async () => {
    state.roomName = 'different-room'
    render(<App />)
    const room = connect()
    await waitFor(() => expect(window.alert).toHaveBeenCalledWith(expect.stringContaining('does not match')))
    expect(room.localParticipant.setMicrophoneEnabled).not.toHaveBeenCalled()
    expect(room.disconnect).toHaveBeenCalled()
  })

  it('can cancel connection setup without a late microphone start', async () => {
    const pending = deferred()
    state.connect = () => pending.promise
    render(<App />)
    const room = connect()
    fireEvent.click(screen.getByRole('button', { name: /Cancel/ }))
    await screen.findByRole('button', { name: /Connect & Start Session/ })
    await act(async () => pending.resolve())
    expect(room.localParticipant.setMicrophoneEnabled).not.toHaveBeenCalled()
    expect(screen.queryByText(/Session Active/)).toBeNull()
  })

  it('attaches remote audio even when it arrives during connection setup', () => {
    const pending = deferred()
    state.connect = () => pending.promise
    render(<App />)
    const room = connect()
    const track = { kind: 'audio', attach: vi.fn(), detach: vi.fn() }
    act(() => room.emit('trackSubscribed', track, {}, { identity: 'agent-pilot' }))
    expect(track.attach).toHaveBeenCalledWith(expect.any(HTMLAudioElement))
  })
})
