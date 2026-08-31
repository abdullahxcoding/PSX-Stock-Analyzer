export default function MacroContext({ sentences }) {
  if (!sentences.length) {
    return <p className="text-sm text-slate-400">No relevant macro factors identified for this company.</p>
  }

  return (
    <ul className="space-y-2">
      {sentences.map((sentence, i) => (
        <li key={i} className="text-sm text-slate-600">
          {sentence}
        </li>
      ))}
    </ul>
  )
}
