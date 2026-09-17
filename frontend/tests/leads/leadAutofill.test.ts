// @vitest-environment node
import { describe, expect, it } from 'vitest'
import {
  composeLeadNotes,
  phoneKey,
  phonesMatch,
  splitFullName
} from '#module-layers/leads/frontend/utils/leadAutofill'

/**
 * The one piece of guessing in the convert flow: how a single enquiry
 * name becomes first_name / last_name, and how the patient notes are
 * composed from the enquiry. Pure functions, so they are tested here
 * instead of through a mounted USlideover.
 */
const LABELS = { motive: 'Motive', availability: 'Availability' }

describe('splitFullName', () => {
  it('splits at the first whitespace', () => {
    expect(splitFullName('Marta Ruiz')).toEqual({ first_name: 'Marta', last_name: 'Ruiz' })
  })

  it('keeps a compound surname together', () => {
    expect(splitFullName('Marta de la Fuente')).toEqual({
      first_name: 'Marta',
      last_name: 'de la Fuente'
    })
  })

  it('leaves the last name empty for a single token', () => {
    expect(splitFullName('Marta')).toEqual({ first_name: 'Marta', last_name: '' })
  })

  it('collapses runs of whitespace and handles empties', () => {
    expect(splitFullName('  Ana   Maria  Gil ')).toEqual({
      first_name: 'Ana',
      last_name: 'Maria Gil'
    })
    expect(splitFullName('')).toEqual({ first_name: '', last_name: '' })
    expect(splitFullName(null)).toEqual({ first_name: '', last_name: '' })
  })
})

describe('composeLeadNotes', () => {
  it('labels the motive and the availability, description verbatim', () => {
    expect(
      composeLeadNotes(
        { motive: 'Ortodoncia', description: 'Viene de Instagram.', availability: 'Tardes' },
        LABELS
      )
    ).toBe('Motive: Ortodoncia\n\nViene de Instagram.\n\nAvailability: Tardes')
  })

  it('skips the fields the enquiry left empty', () => {
    expect(composeLeadNotes({ motive: 'Ortodoncia', availability: null }, LABELS)).toBe(
      'Motive: Ortodoncia'
    )
    expect(composeLeadNotes({}, LABELS)).toBe('')
  })
})

describe('phoneKey / phonesMatch', () => {
  it('compares the trailing 9 digits', () => {
    expect(phoneKey('+34 600 111 222')).toBe('600111222')
    expect(phonesMatch('600 111 222', '600111222')).toBe(true)
    expect(phonesMatch('+34 600 111 222', '600111222')).toBe(true)
    expect(phonesMatch('600111223', '600111222')).toBe(false)
  })

  it('never matches on an empty number', () => {
    expect(phonesMatch(null, '600111222')).toBe(false)
    expect(phonesMatch('', '')).toBe(false)
  })
})
