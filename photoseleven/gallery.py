from flask import Blueprint, current_app, request, Response, stream_with_context
from photoseleven.auth import login_required
from photoseleven.error import only_multimedia_content, response_fail, response_success
import os

bp = Blueprint('gallery', __name__, url_prefix='/api/gallery')


class GalleryErrors:
    GAL_ERR_MEDIA_EXISTS = 'GAL_ERR_MEDIA_EXISTS'
    GAL_ERR_MEDIA_NOT_EXIST = 'GAL_ERR_MEDIA_NOT_EXIST'
    GAL_ERR_UNSUPPORTED = 'GAL_ERR_UNSUPPORTED'

# @bp.route('/photos', methods=('GET', 'POST', 'DELETE'))
# @login_required
# def photos():
#     @only_multipart_content
#     def post_photo():


@bp.route('/media/<file_id>', methods=('GET', 'POST'))
@login_required
def media(file_id):
    """To post and get multimedia files"""

    chunk_size = 1048576  # 1 MB

    @only_multimedia_content
    def post_multimedia(filename):
        if len(filename) < 3 or filename[-3:] not in current_app.config['ALLOWED_MEDIA_EXT']:
            return response_fail(GalleryErrors.GAL_ERR_UNSUPPORTED, 403)

        save_path = os.path.join(current_app.config['UPLOADS_DIR'], filename)
        if os.path.exists(save_path):
            return response_fail(GalleryErrors.GAL_ERR_MEDIA_EXISTS, 403)

        with open(save_path, 'wb') as media_file:
            while True:
                chunk = request.stream.read(chunk_size)
                if len(chunk) == 0:
                    break
                media_file.write(chunk)

        return response_success(201)

    if request.method == 'POST':
        return post_multimedia(file_id)

    if request.method == 'GET':
        if len(file_id) < 3 or file_id[-3:] not in current_app.config['ALLOWED_MEDIA_EXT']:
            return response_fail(GalleryErrors.GAL_ERR_UNSUPPORTED, 403)

        load_path = os.path.join(current_app.config['UPLOADS_DIR'], file_id)
        if not os.path.exists(load_path):
            return response_fail(GalleryErrors.GAL_ERR_MEDIA_NOT_EXIST, 403)

        def generate(file_path):
            with open(file_path, 'rb') as media_file:
                while True:
                    chunk = media_file.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        return Response(stream_with_context(generate(load_path)),
                        mimetype=current_app.config['ALLOWED_MEDIA_EXT'][file_id[-3:]])
