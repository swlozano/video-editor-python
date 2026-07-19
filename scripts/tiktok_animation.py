from PIL import Image

def create_black_background(width, height, output_file='black_background.png'):
    """
    Creates a black image with the specified size.

    Parameters:
        width (int): image width in pixels
        height (int): image height in pixels
        output_file (str): output file name/path

    Returns:
        Image: the created black background
    """
    img = Image.new('RGB', (width, height), color=(0, 0, 0))
    img.save(output_file)
    print(f'Image created: {output_file} ({width}x{height})')
    return img


def paste_scaled_image(background, image_path, y=0, x=None):
    """
    Pastes an image onto the background, resizing it so it takes up the
    full width of the background while keeping its original aspect ratio
    (the height is adjusted automatically).

    Parameters:
        background (Image): background image (PIL.Image object) to paste onto
        image_path (str): path of the image to paste
        y (int): vertical position where the image will be pasted (default 0, top)
        x (int): horizontal position where the image will be pasted (default: centered)

    Returns:
        Image: the background with the image already pasted on it
    """
    image = Image.open(image_path)

    # Convert to RGBA to support transparency if the image has it
    if image.mode != 'RGBA':
        image = image.convert('RGBA')

    bg_width = background.width

    # Calculate the new height while keeping the original aspect ratio
    ratio = image.height / image.width
    new_height = int(bg_width * ratio)

    resized_image = image.resize((bg_width, new_height), Image.LANCZOS)

    # If x is not specified, center it horizontally (will be 0 since it spans the full width)
    if x is None:
        x = (bg_width - resized_image.width) // 2

    # Make sure the background supports transparency when pasting
    if background.mode != 'RGBA':
        background = background.convert('RGBA')

    background.paste(resized_image, (x, y), resized_image)

    return background


def paste_image_bottom_at_middle(background, image_path, x=None):
    """
    Pastes an image onto the background, scaling it to the background's
    full width (keeping aspect ratio), and positions it so that the
    BOTTOM edge of the image sits exactly at the vertical middle of
    the background.

    Parameters:
        background (Image): background image (PIL.Image object) to paste onto
        image_path (str): path of the image to paste
        x (int): horizontal position (default: centered)

    Returns:
        Image: the background with the image already pasted on it
    """
    image = Image.open(image_path)

    if image.mode != 'RGBA':
        image = image.convert('RGBA')

    bg_width = background.width
    bg_height = background.height

    # Resize keeping aspect ratio, matching the background's width
    ratio = image.height / image.width
    new_height = int(bg_width * ratio)
    resized_image = image.resize((bg_width, new_height), Image.LANCZOS)

    # Bottom of the image must land exactly at the middle of the background,
    # so its top (y) is: middle - image_height
    y = (bg_height // 2) - new_height

    if x is None:
        x = (bg_width - resized_image.width) // 2

    if background.mode != 'RGBA':
        background = background.convert('RGBA')

    background.paste(resized_image, (x, y), resized_image)

    return background


if __name__ == '__main__':
    # Usage example: change these values as needed
    WIDTH = 1080
    HEIGHT = 1920

    background = create_black_background(WIDTH, HEIGHT)

    # Paste an image so its bottom edge sits right above the middle of the background
    background = paste_image_bottom_at_middle(background, 'in/03.jpg')

    background.save('result.png')
    print('Combined image saved as result.png')