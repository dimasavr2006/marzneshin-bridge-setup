# Custom Landing Page

Place your custom HTML/CSS files here to replace the default Confluence template.

## Usage

1. Add your files to this directory (e.g., `index.html`, `style.css`, images)
2. Run the setup script
3. Caddy will serve your custom page instead of the default template

## Example Structure

```
custom/
├── index.html
├── css/
│   └── style.css
├── js/
│   └── script.js
└── images/
    └── logo.png
```

## Requirements

- `index.html` is required as the entry point
- All assets should use relative paths
- The page will be served at `https://your-domain.com/`

## Notes

- If this directory is empty or doesn't exist, the default Confluence template will be used
- You can update the custom page after installation by modifying files in the server's `caddy/templates/` directory