import React from 'react';

const MarkdownRenderer = ({ content }) => {
  const processMarkdown = (text) => {
    if (!text || typeof text !== 'string') return '';
    
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/^#{1,6}\s+(.*$)/gm, '<h3>$1</h3>')
      .replace(/^=+$/gm, '')
      .replace(/^-+$/gm, '')
      .replace(/^\s*[-*+]\s+(.*)$/gm, '• $1')
      .replace(/^\s*\d+\.\s+(.*)$/gm, '$1');
  };

  return (
    <div 
      className="markdown-content"
      dangerouslySetInnerHTML={{ __html: processMarkdown(content) }}
      style={{
        whiteSpace: 'pre-wrap',
        lineHeight: '1.4'
      }}
    />
  );
};

export default MarkdownRenderer;