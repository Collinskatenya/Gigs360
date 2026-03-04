import os
from io import BytesIO
from django.conf import settings
from django.template.loader import get_template
from xhtml2pdf import pisa

def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those resources.
    Critical for rendering Logos, Profile Pictures, and CSS in the PDF without HTTP overhead.
    """
    sUrl = settings.STATIC_URL      # Typically '/static/'
    sRoot = getattr(settings, 'STATIC_ROOT', None)    # Typically '/home/userX/project/static/'
    mUrl = settings.MEDIA_URL       # Typically '/media/'
    mRoot = getattr(settings, 'MEDIA_ROOT', None)     # Typically '/home/userX/project/media/'

    # Convert URIs to absolute system paths
    if uri.startswith(mUrl):
        # Fallback to URI if mRoot is not configured (prevents os.path.join TypeError)
        if mRoot:
            path = os.path.join(mRoot, uri.replace(mUrl, ""))
        else:
            return uri
            
    elif uri.startswith(sUrl):
        path = ""
        # 1. Try STATIC_ROOT (Production scenario where collectstatic has run)
        if sRoot:
            path = os.path.join(sRoot, uri.replace(sUrl, ""))
        
        # 2. Fallback for Development (DEBUG=True) where static files are scattered
        if not os.path.isfile(path) and settings.DEBUG:
            for static_dir in getattr(settings, 'STATICFILES_DIRS', []):
                dev_path = os.path.join(static_dir, uri.replace(sUrl, ""))
                if os.path.isfile(dev_path):
                    path = dev_path
                    break
    else:
        return uri  # Handle absolute HTTP URIs (e.g. http://some.tld/foo.png)

    # Safety Net: If the file physically doesn't exist on the drive, 
    # return the original URI and let xhtml2pdf try to fetch it via HTTP as a last resort.
    if not os.path.isfile(path):
        return uri
            
    return path

def render_to_pdf(template_src, context_dict={}):
    """
    Renders a Django HTML template into a raw PDF byte string.
    Decoupled from HttpResponse to allow for email attachments or direct downloads.
    """
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    
    # Generate PDF
    # encoding='UTF-8' is CRITICAL for Currency Symbols (KES, $, €)
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result, link_callback=link_callback)
    
    if not pdf.err:
        return result.getvalue()
        
    return None