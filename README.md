dashboard
=========

Web-based reporting dashboard to aggregate stats about Tsumanga's games from multiple sources

To run the web pages for testing:

    python3 -m dashboard.startweb --port=8880 --config=local --static=here

All web pages are on URLs beginning with /dashboard

To run the web services:

    python3 -m dashboard.startapp --port=8980 --config=local

All web services are on URLs beginning with /app/dash

They can be included in other Tsumanga web sites using --imports dashboard.pages or --imports dashboard.services respectively.
