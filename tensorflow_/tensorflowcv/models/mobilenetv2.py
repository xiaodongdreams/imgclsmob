"""
    MobileNetV2, implemented in TensorFlow.
    Original paper: 'MobileNetV2: Inverted Residuals and Linear Bottlenecks,' https://arxiv.org/abs/1801.04381.
"""

__all__ = ['MobileNetV2', 'mobilenetv2_w1', 'mobilenetv2_w3d4', 'mobilenetv2_wd2', 'mobilenetv2_wd4']

import os
import tensorflow as tf
from .common import conv2d, batchnorm


def mobnet_conv(x,
                in_channels,
                out_channels,
                kernel_size,
                strides,
                padding,
                groups,
                activate,
                training,
                name="mobnet_conv"):
    """
    MobileNetV2 specific convolution block.

    Parameters:
    ----------
    x : Tensor
        Input tensor.
    in_channels : int
        Number of input channels.
    out_channels : int
        Number of output channels.
    kernel_size : int or tuple/list of 2 int
        Convolution window size.
    strides : int or tuple/list of 2 int
        Strides of the convolution.
    padding : int or tuple/list of 2 int
        Padding value for convolution layer.
    groups : int
        Number of groups.
    activate : bool
        Whether activate the convolution block.
    training : bool, or a TensorFlow boolean scalar tensor
      Whether to return the output in training mode or in inference mode.
    name : str, default 'mobnet_conv'
        Block name.

    Returns
    -------
    Tensor
        Resulted tensor.
    """
    x = conv2d(
        x=x,
        in_channels=in_channels,
        out_channels=out_channels,
        kernel_size=kernel_size,
        strides=strides,
        padding=padding,
        groups=groups,
        use_bias=False,
        name=name + "/conv")
    x = batchnorm(
        x=x,
        training=training,
        name=name + "/bn")
    if activate:
        x = tf.nn.relu6(x, name=name + "/activ")
    return x


def mobnet_conv1x1(x,
                   in_channels,
                   out_channels,
                   activate,
                   training,
                   name="mobnet_conv1x1"):
    """
    1x1 version of the MobileNetV2 specific convolution block.

    Parameters:
    ----------
    x : Tensor
        Input tensor.
    in_channels : int
        Number of input channels.
    out_channels : int
        Number of output channels.
    activate : bool
        Whether activate the convolution block.
    training : bool, or a TensorFlow boolean scalar tensor
      Whether to return the output in training mode or in inference mode.
    name : str, default 'mobnet_conv1x1'
        Block name.

    Returns
    -------
    Tensor
        Resulted tensor.
    """
    return mobnet_conv(
        x=x,
        in_channels=in_channels,
        out_channels=out_channels,
        kernel_size=1,
        strides=1,
        padding=0,
        groups=1,
        activate=activate,
        training=training,
        name=name)


def mobnet_dwconv3x3(x,
                     in_channels,
                     out_channels,
                     strides,
                     activate,
                     training,
                     name="mobnet_dwconv3x3"):
    """
    3x3 depthwise version of the MobileNetV2 specific convolution block.

    Parameters:
    ----------
    x : Tensor
        Input tensor.
    in_channels : int
        Number of input channels.
    out_channels : int
        Number of output channels.
    strides : int or tuple/list of 2 int
        Strides of the convolution.
    activate : bool
        Whether activate the convolution block.
    training : bool, or a TensorFlow boolean scalar tensor
      Whether to return the output in training mode or in inference mode.
    name : str, default 'mobnet_dwconv3x3'
        Block name.

    Returns
    -------
    Tensor
        Resulted tensor.
    """
    return mobnet_conv(
        x=x,
        in_channels=in_channels,
        out_channels=out_channels,
        kernel_size=3,
        strides=strides,
        padding=1,
        groups=out_channels,
        activate=activate,
        training=training,
        name=name)


def linear_bottleneck(x,
                      in_channels,
                      out_channels,
                      strides,
                      expansion,
                      training,
                      name="linear_bottleneck"):
    """
    So-called 'Linear Bottleneck' layer. It is used as a MobileNetV2 unit.

    Parameters:
    ----------
    x : Tensor
        Input tensor.
    in_channels : int
        Number of input channels.
    out_channels : int
        Number of output channels.
    strides : int or tuple/list of 2 int
        Strides of the convolution.
    expansion : bool
        Whether do expansion of channels.
    training : bool, or a TensorFlow boolean scalar tensor
      Whether to return the output in training mode or in inference mode.
    name : str, default 'linear_bottleneck'
        Unit name.

    Returns
    -------
    Tensor
        Resulted tensor.
    """
    residual = (in_channels == out_channels) and (strides == 1)
    mid_channels = in_channels * 6 if expansion else in_channels

    if residual:
        identity = x

    x = mobnet_conv1x1(
        x=x,
        in_channels=in_channels,
        out_channels=mid_channels,
        activate=True,
        training=training,
        name=name + "/conv1")
    x = mobnet_dwconv3x3(
        x=x,
        in_channels=mid_channels,
        out_channels=mid_channels,
        strides=strides,
        activate=True,
        training=training,
        name=name + "/conv2")
    x = mobnet_conv1x1(
        x=x,
        in_channels=mid_channels,
        out_channels=out_channels,
        activate=False,
        training=training,
        name=name + "/conv3")

    if residual:
        x = x + identity

    return x


class MobileNetV2(object):
    """
    MobileNetV2 model from 'MobileNetV2: Inverted Residuals and Linear Bottlenecks,' https://arxiv.org/abs/1801.04381.

    Parameters:
    ----------
    channels : list of list of int
        Number of output channels for each unit.
    init_block_channels : int
        Number of output channels for the initial unit.
    final_block_channels : int
        Number of output channels for the final block of the feature extractor.
    in_channels : int, default 3
        Number of input channels.
    in_size : tuple of two ints, default (224, 224)
        Spatial size of the expected input image.
    classes : int, default 1000
        Number of classification classes.
    """
    def __init__(self,
                 channels,
                 init_block_channels,
                 final_block_channels,
                 in_channels=3,
                 in_size=(224, 224),
                 classes=1000,
                 **kwargs):
        super(MobileNetV2, self).__init__(**kwargs)
        self.channels = channels
        self.init_block_channels = init_block_channels
        self.final_block_channels = final_block_channels
        self.in_channels = in_channels
        self.in_size = in_size
        self.classes = classes

    def __call__(self,
                 x,
                 training=False):
        """
        Build a model graph.

        Parameters:
        ----------
        x : Tensor
            Input tensor.
        training : bool, or a TensorFlow boolean scalar tensor, default False
          Whether to return the output in training mode or in inference mode.

        Returns
        -------
        Tensor
            Resulted tensor.
        """
        in_channels = self.in_channels
        x = mobnet_conv(
            x=x,
            in_channels=in_channels,
            out_channels=self.init_block_channels,
            kernel_size=3,
            strides=2,
            padding=1,
            groups=1,
            activate=True,
            training=training,
            name="features/init_block")
        in_channels = self.init_block_channels
        for i, channels_per_stage in enumerate(self.channels):
            for j, out_channels in enumerate(channels_per_stage):
                strides = 2 if (j == 0) and (i != 0) else 1
                expansion = (i != 0) or (j != 0)
                x = linear_bottleneck(
                    x=x,
                    in_channels=in_channels,
                    out_channels=out_channels,
                    strides=strides,
                    expansion=expansion,
                    training=training,
                    name="features/stage{}/unit{}".format(i + 1, j + 1))
                in_channels = out_channels
        x = mobnet_conv1x1(
            x=x,
            in_channels=in_channels,
            out_channels=self.final_block_channels,
            activate=True,
            training=training,
            name="features/final_block")
        in_channels = self.final_block_channels
        x = tf.layers.average_pooling2d(
            inputs=x,
            pool_size=7,
            strides=1,
            data_format='channels_first',
            name="features/final_pool")

        x = conv2d(
            x=x,
            in_channels=in_channels,
            out_channels=self.classes,
            kernel_size=1,
            use_bias=False,
            name="output")
        x = tf.layers.flatten(x)

        return x


def get_mobilenetv2(width_scale,
                    model_name=None,
                    pretrained=False,
                    root=os.path.join('~', '.tensorflow', 'models'),
                    **kwargs):
    """
    Create MobileNetV2 model with specific parameters.

    Parameters:
    ----------
    width_scale : float
        Scale factor for width of layers.
    model_name : str or None, default None
        Model name for loading pretrained model.
    pretrained : bool, default False
        Whether to load the pretrained weights for model.
    root : str, default '~/.tensorflow/models'
        Location for keeping the model parameters.

    Returns
    -------
    functor
        Functor for model graph creation with extra fields.
    """

    init_block_channels = 32
    final_block_channels = 1280
    layers = [1, 2, 3, 4, 3, 3, 1]
    downsample = [0, 1, 1, 1, 0, 1, 0]
    channels_per_layers = [16, 24, 32, 64, 96, 160, 320]

    from functools import reduce
    channels = reduce(lambda x, y: x + [[y[0]] * y[1]] if y[2] != 0 else x[:-1] + [x[-1] + [y[0]] * y[1]],
                      zip(channels_per_layers, layers, downsample), [[]])

    if width_scale != 1.0:
        channels = [[int(cij * width_scale) for cij in ci] for ci in channels]
        init_block_channels = int(init_block_channels * width_scale)
        if width_scale > 1.0:
            final_block_channels = int(final_block_channels * width_scale)

    net = MobileNetV2(
        channels=channels,
        init_block_channels=init_block_channels,
        final_block_channels=final_block_channels,
        **kwargs)

    if pretrained:
        if (model_name is None) or (not model_name):
            raise ValueError("Parameter `model_name` should be properly initialized for loading pretrained model.")
        from .model_store import download_state_dict
        net.state_dict, net.file_path = download_state_dict(
            model_name=model_name,
            local_model_store_dir_path=root)
    else:
        net.state_dict = None
        net.file_path = None

    return net


def mobilenetv2_w1(**kwargs):
    """
    1.0 MobileNetV2-224 model from 'MobileNetV2: Inverted Residuals and Linear Bottlenecks,'
    https://arxiv.org/abs/1801.04381.

    Parameters:
    ----------
    pretrained : bool, default False
        Whether to load the pretrained weights for model.
    root : str, default '~/.tensorflow/models'
        Location for keeping the model parameters.

    Returns
    -------
    functor
        Functor for model graph creation with extra fields.
    """
    return get_mobilenetv2(width_scale=1.0, model_name="mobilenetv2_w1", **kwargs)


def mobilenetv2_w3d4(**kwargs):
    """
    0.75 MobileNetV2-224 model from 'MobileNetV2: Inverted Residuals and Linear Bottlenecks,'
    https://arxiv.org/abs/1801.04381.

    Parameters:
    ----------
    pretrained : bool, default False
        Whether to load the pretrained weights for model.
    root : str, default '~/.tensorflow/models'
        Location for keeping the model parameters.

    Returns
    -------
    functor
        Functor for model graph creation with extra fields.
    """
    return get_mobilenetv2(width_scale=0.75, model_name="mobilenetv2_w3d4", **kwargs)


def mobilenetv2_wd2(**kwargs):
    """
    0.5 MobileNetV2-224 model from 'MobileNetV2: Inverted Residuals and Linear Bottlenecks,'
    https://arxiv.org/abs/1801.04381.

    Parameters:
    ----------
    pretrained : bool, default False
        Whether to load the pretrained weights for model.
    root : str, default '~/.tensorflow/models'
        Location for keeping the model parameters.

    Returns
    -------
    functor
        Functor for model graph creation with extra fields.
    """
    return get_mobilenetv2(width_scale=0.5, model_name="mobilenetv2_wd2", **kwargs)


def mobilenetv2_wd4(**kwargs):
    """
    0.25 MobileNetV2-224 model from 'MobileNetV2: Inverted Residuals and Linear Bottlenecks,'
    https://arxiv.org/abs/1801.04381.

    Parameters:
    ----------
    pretrained : bool, default False
        Whether to load the pretrained weights for model.
    root : str, default '~/.tensorflow/models'
        Location for keeping the model parameters.

    Returns
    -------
    functor
        Functor for model graph creation with extra fields.
    """
    return get_mobilenetv2(width_scale=0.25, model_name="mobilenetv2_wd4", **kwargs)


def _test():
    import numpy as np
    from .model_store import init_variables_from_state_dict

    pretrained = False

    models = [
        mobilenetv2_w1,
        mobilenetv2_w3d4,
        mobilenetv2_wd2,
        mobilenetv2_wd4,
    ]

    for model in models:

        net = model(pretrained=pretrained)
        x = tf.placeholder(
            dtype=tf.float32,
            shape=(None, 3, 224, 224),
            name='xx')
        y_net = net(x)

        weight_count = np.sum([np.prod(v.get_shape().as_list()) for v in tf.trainable_variables()])
        print("m={}, {}".format(model.__name__, weight_count))
        assert (model != mobilenetv2_w1 or weight_count == 3504960)
        assert (model != mobilenetv2_w3d4 or weight_count == 2627592)
        assert (model != mobilenetv2_wd2 or weight_count == 1964736)
        assert (model != mobilenetv2_wd4 or weight_count == 1516392)

        with tf.Session() as sess:
            if pretrained:
                init_variables_from_state_dict(sess=sess, state_dict=net.state_dict)
            else:
                sess.run(tf.global_variables_initializer())
            x_value = np.zeros((1, 3, 224, 224), np.float32)
            y = sess.run(y_net, feed_dict={x: x_value})
            assert (y.shape == (1, 1000))
        tf.reset_default_graph()


if __name__ == "__main__":
    _test()
