export default function DotSpinner() {
  return (
    <div className="flex items-center justify-center space-x-2">
      <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
      <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
      <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" />
    </div>
  );
}