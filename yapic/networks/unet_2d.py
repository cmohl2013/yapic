import keras
import logging
import os
import math

logger = logging.getLogger(os.path.basename(__file__))


def convolve(net, n_filters, filter_size):
    '''
    double convolution step
    '''
    net = keras.layers.Conv2D(n_filters,
                              filter_size,
                              activation='relu',
                              kernel_initializer='glorot_normal',
                              data_format='channels_last')(net)
    net = keras.layers.Conv2D(n_filters,
                              filter_size,
                              activation='relu',
                              kernel_initializer='glorot_normal',
                              data_format='channels_last')(net)
    return net


def contract(net, n_filters):
    net = convolve(net, n_filters, (3, 3))
    to_concat = net

    net = keras.layers.MaxPooling2D(pool_size=(2, 2),
                                    data_format='channels_last')(net)
    return net, to_concat


def expand(net, to_concat, n_filters):
    net = keras.layers.UpSampling2D(size=(2, 2),
                                    data_format='channels_last')(net)
    net = convolve(net, n_filters, (2, 2))

    shape_diff = to_concat.shape[-2] - net.shape[-2]
    print('net: {}'.format(net.shape))
    print('to_concat: {}'.format(to_concat.shape))

    print('d: {}'.format(shape_diff))
    cropping = int(math.floor(int(shape_diff)/2.))
    print('crop: {}'.format(cropping))
    cropped = keras.layers.Cropping2D(cropping=cropping,
                                      data_format='channels_last')(to_concat)

    net = keras.layers.Concatenate(axis=-1)([net, cropped])
    net = convolve(net, n_filters, (3, 3))

    return net


def build_network(N_classes, input_size_czxy):
    '''
    Builds the original U-Net by Ronneberger et al. (2015) for 2d images
    '''
    logger.debug('Building network with {} classes'.format(N_classes))

    assert len(input_size_czxy) == 4

    N_channels = input_size_czxy[0]
    size_z = input_size_czxy[1]
    size_xy = input_size_czxy[3]

    assert N_classes >= 2
    assert N_channels >= 1
    assert size_z == 1
    assert input_size_czxy[2] == input_size_czxy[3]

    net = keras.layers.Input(shape=(size_z, size_xy, size_xy, N_channels))
    input_net = net

    net = keras.layers.Reshape((size_xy, size_xy, N_channels))(net)

    net, to_concat_1 = contract(net, 64)
    net, to_concat_2 = contract(net, 128)
    net, to_concat_3 = contract(net, 256)
    net, to_concat_4 = contract(net, 512)
    net, to_concat_5 = contract(net, 1024)
    net = expand(to_concat_5, to_concat_4, 512)
    net = expand(net, to_concat_3, 256)
    net = expand(net, to_concat_2, 128)
    net = expand(net, to_concat_1, 64)

    net = keras.layers.Conv2D(N_classes,
                              (1, 1),
                              activation='softmax',
                              data_format='channels_last')(net)
    print('net: {}'.format(net.shape))


    size_xy_out = net.shape[-2].value
    print('net: {}'.format(net.shape))
    net = keras.layers.Reshape((1, size_xy_out, size_xy_out, N_classes))(net)
    print('net: {}'.format(net.shape))
    model = keras.models.Model(inputs=input_net, outputs=net)


    return model
