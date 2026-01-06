import os
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from xhtml2pdf import pisa

def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those resources.
    Critical for rendering Logos, Profile Pictures, and CSS in the PDF.
    """
    sUrl = settings.STATIC_URL      # Typically /static/
    sRoot = settings.STATIC_ROOT    # Typically /home/userX/project/static/
    mUrl = settings.MEDIA_URL       # Typically /media/
    mRoot = settings.MEDIA_ROOT     # Typically /home/userX/project/media/

    # Convert URIs to absolute system paths
    if uri.startswith(mUrl):
        path = os.path.join(mRoot, uri.replace(mUrl, ""))
    elif uri.startswith(sUrl):
        # 1. Try STATIC_ROOT (Production scenario where collectstatic has run)
        path = os.path.join(sRoot, uri.replace(sUrl, ""))
        
        # 2. Fallback for Development (DEBUG=True) where static files are scattered
        if not os.path.isfile(path) and settings.DEBUG:
            for static_dir in settings.STATICFILES_DIRS:
                dev_path = os.path.join(static_dir, uri.replace(sUrl, ""))
                if os.path.isfile(dev_path):
                    path = dev_path
                    break
    else:
        return uri  # Handle absolute URIs (e.g. http://some.tld/foo.png)

    # Ensure the file exists, or the PDF engine might crash
    if not os.path.isfile(path):
        # Fail silently by returning None, or log error
        # print(f"PDF Gen Warning: Asset not found at {path}")
        return None
            
    return path

def render_to_pdf(template_src, context_dict={}):
    """
    Renders a Django HTML template into a PDF file.
    """
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    
    # Generate PDF
    # encoding='UTF-8' is CRITICAL for Currency Symbols (KES, $, €)
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, link_callback=link_callback)
    
    if not pdf.err:
        # FIX: Return the raw bytes, not an HttpResponse.
        # The View (views.py) will wrap this in an HttpResponse with the correct headers.
        return result.getvalue()
        
    return None