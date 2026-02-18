export default function Message({ message }) {
  const isUser = message.type === 'user';

  return (
    <div className={`flex gap-4 mb-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
        isUser ? 'bg-surface-light text-light' : 'bg-surface text-light'
      }`}>
        {isUser ? 'U' : 'A'}
      </div>

      <div className={`flex-1 max-w-2xl ${isUser ? 'text-right' : 'text-left'}`}>
        <div className={`inline-block px-4 py-2 rounded-lg ${
          isUser
            ? 'bg-surface-light text-light rounded-br-none'
            : 'bg-surface text-light rounded-bl-none'
        }`}>
          {message.imageUrl && (
            <img
              src={message.imageUrl}
              alt="Uploaded"
              className="w-full max-w-md mb-3 rounded-lg border border-border object-cover"
            />
          )}
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    </div>
  );
}
